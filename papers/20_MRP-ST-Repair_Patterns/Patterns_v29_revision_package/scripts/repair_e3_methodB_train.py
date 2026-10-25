#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""repair_e3_methodB_train.py — MRP-ST-Repair 方法 B：训练态患者对抗修复（E3 go/no-go）。

背景（E1 结论）
---------------
E1 已证 post-hoc 患者块投影不可行：LDI 降门下时 LOO tau 同步翻转负值而 in-sample
tau 保留 —— 泄漏成分与可泛化空间信息在切片均值子空间不可分离，修复约束必须在
生成嵌入时施加。本脚本把约束移入训练：空间图注意自编码器 + GRL 患者对抗。

数据口径（与审计论文 train_st.py 完全一致）
-------------------------------------------
- discover(): _is_visium_dir + 一层嵌套扫描（geo_ectocervix/{P00x} 等）
- load_sample(): 逐样本读 10x h5（标准/HD 双路径）
- 表达预处理: per-sample top-2000 variance genes → log1p → union panel 零填充对齐
  （train_st.py 同口径：union 而非 intersection，保留 HPV 相关基因）
- 空间图: coords 按 si*10000 偏移（train_st.py 同口径，切片间永不连边）后
  radius_neighbors_graph(rad_cutoff=150, fullres px, STAGATE Radius 模式同单位)

模型
----
encoder : GATConv(in→512) + ELU + GATConv(512→128)   （STAGATE 式两层空间图注意）
decoder : Linear(128→in)，MSE 重构
adversary: MLP(128→64→35)，GRL 梯度反转，迫使嵌入不编码患者（切片）身份

评估（审计仪器，refit 置换 B=10000、seed=20261010）
--------------------------------------------------
spot 级 Z 按样本均值池化（severity_of 过滤）→ X(35×128), y(0/1/2)
- tau_lodo + p_refit : refit_grid_audit.audit()
- sigma_null        : 同 seed 置换分布 SD（与 E1 完全一致）
- LDI               = (tau_lodo − 0.001) / sigma_null
- tau_insample      : refit_grid_audit.insample_tau()（机制诊断量）

判定（方案 §6 E3，与 E1 修正版口径一致）
---------------------------------------
go = 存在 λ_adv>0 使 LDI<1.645 且 tau_lodo ≥ 0.70 × tau_lodo(λ=0)
     （保真量 = LOO tau；in-sample tau 仅作机制对照另行报告）

用法（服务器，务必 screen）
---------------------------
screen -S mb_repair
python scripts/repair_e3_methodB_train.py \
    --data data/st_visium/cervix_all_ext --device cuda:0
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from src import st_data as S  # noqa: E402  审计同入口
from refit_grid_audit import audit, insample_tau, operator, kendall_tau  # noqa: E402
from probe_lodo import severity_of  # noqa: E402

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402

TAU_PERP = 0.001
LDI_GATE = 1.645
FIDELITY_KEEP = 0.70
PERM_SEED = 20261010


def memtrace(tag):
    """MEMTRACE=1 时打印当前进程 RSS，用于定位内存峰值来源。"""
    import os
    if not os.environ.get("MEMTRACE"):
        return
    with open("/proc/self/statm") as f:
        rss = int(f.read().split()[1]) * 4096 / 2**20
    print(f"[mem] {tag}: RSS={rss:.0f} MiB", flush=True)


# ---------------------------------------------------------------- 模型
class ReverseLayerF(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, alpha):
        ctx.alpha = alpha
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output.neg() * ctx.alpha, None


class MethodB(nn.Module):
    """STAGATE 式空间 GAT 编码器 + 线性解码 + 患者对抗头。"""

    def __init__(self, in_dim, n_patients, hid=512, out=128, sn=False,
                 backbone='gat', n_classes=0):
        super().__init__()
        from torch_geometric.nn import GATConv, GCNConv
        self.bb = backbone
        if backbone == 'mlp':
            # 结构无关对照（E5-c）：不使用空间图，与跨域审计所用编码器同族。
            # 前向忽略边索引，解码器/对抗头/GRL/损失全部不变，
            # 故 GAT→MLP 只改变"是否使用空间邻接"这一件事。
            self.conv1 = nn.Linear(in_dim, hid)
            self.conv2 = nn.Linear(hid, out)
        elif backbone == 'gcn':
            # 骨干通用性消融（方案 E5：至少两骨干）——GCNConv 同签名替换
            self.conv1 = GCNConv(in_dim, hid)
            self.conv2 = GCNConv(hid, out)
        else:
            self.conv1 = GATConv(in_dim, hid, heads=1, concat=True)
            self.conv2 = GATConv(hid, out, heads=1, concat=True)
        self.dec = nn.Linear(out, in_dim)
        # 实验 A 对比臂：IRM 需要线性标签读出头（n_classes>0 时启用；
        # method=mrp/groupdro 时 n_classes=0 → self.lhead=None → 前向路径与
        # 原实现逐位一致，保证既有结果可复现）
        self.lhead = nn.Linear(out, n_classes) if n_classes else None

        def _lin(i, o):
            l = nn.Linear(i, o)
            # 稳定三件套之三：对抗头谱归一化（GAN 谱归一化判别器同款），
            # 抑制对抗头容量爆炸导致的 GRL 振荡（§9.2 种子间 LDI SD 1.0-1.8）
            if sn:
                return nn.utils.parametrizations.spectral_norm(l)
            return l

        self.adv = nn.Sequential(_lin(out, 64), nn.ReLU(),
                                 _lin(64, n_patients))

    def encode(self, x, ei):
        if self.bb == 'mlp':
            return self.conv2(F.elu(self.conv1(x)))
        return self.conv2(F.elu(self.conv1(x, ei)), ei)


# ---------------------------------------------------------------- 数据
def _is_visium_dir(d: Path) -> bool:
    if (d / "filtered_feature_bc_matrix.h5").exists():
        return True
    br = d / "binned_outputs"
    if br.exists():
        return any((s / "filtered_feature_bc_matrix.h5").exists()
                    for s in br.iterdir() if s.is_dir())
    return False


def discover(root: Path):
    """train_st.py 同逻辑：直查 + 一层嵌套，resolve 去重。"""
    if _is_visium_dir(root):
        return [root]
    direct = [d for d in sorted(root.iterdir()) if _is_visium_dir(d)]
    nested = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and not _is_visium_dir(d):
            nested.extend([s for s in sorted(d.iterdir()) if _is_visium_dir(s)])
    out, seen = [], set()
    for sd in direct + nested:
        rp = sd.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(sd)
    return out


def load_cohort(data_root: Path, n_genes: int):
    """35 切片 → union-panel 对齐表达矩阵 + 偏移坐标 + 样本切片表。"""
    dirs = discover(data_root)
    print(f"[discover] {len(dirs)} sample dirs", flush=True)
    per_exp, per_genes, per_coords, slices = [], [], [], []
    panel, seen = [], set()
    total = 0
    for si, sd in enumerate(dirs):
        t0 = time.time()
        sample = S.load_sample(sd)
        Xd = np.asarray(sample.expression.todense(), dtype=np.float32)
        names = list(sample.genes)
        keep = (np.argsort(Xd.var(axis=0))[::-1][:n_genes]
                if Xd.shape[1] > n_genes else np.arange(Xd.shape[1]))
        Xk = np.log1p(Xd[:, keep])
        gk = [names[i] for i in keep]
        coords = np.asarray(sample.coords, dtype=np.float64) + si * 50000.0
        per_exp.append(Xk)
        per_genes.append(gk)
        per_coords.append(coords)
        for g in gk:
            if g not in seen:
                seen.add(g)
                panel.append(g)
        slices.append((sd.name, total, total + Xk.shape[0]))
        total += Xk.shape[0]
        print(f"  loaded {sd.name}: {Xk.shape[0]} spots "
              f"({time.time() - t0:.1f}s)", flush=True)

    gidx = {g: i for i, g in enumerate(panel)}
    X = np.zeros((total, len(panel)), dtype=np.float32)
    for Xk, gk, (nm, n0, n1) in zip(per_exp, per_genes, slices):
        for j, g in enumerate(gk):
            X[n0:n1, gidx[g]] = Xk[:, j]
    coords = np.vstack(per_coords)
    print(f"[cohort] spots={X.shape[0]} union_genes={X.shape[1]}", flush=True)
    return X, coords, slices, panel


def build_edge_index(coords, k=6):
    """kNN 空间图（k=6，train_st.build_neighbor_targets 同口径）。
    50000 偏移远大于单切片 extent，kNN 永不跨样本取邻居。
    （v1 用 rad=150 半径图在 fullres px 下产生 5.05M 边导致 4080 OOM，
    v2 改 kNN 后边数 ~66 万，图结构与审计管线一致。）"""
    from scipy.spatial import cKDTree
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=k + 1)  # 含自身
    src = np.repeat(np.arange(len(coords)), k)
    dst = idx[:, 1:].ravel()
    keep = dst != src  # 剔除意外自环
    ei = torch.tensor(np.vstack([src[keep], dst[keep]]), dtype=torch.long)
    # 双向边（GATConv MessagePassing 按有向边聚合）
    ei = torch.cat([ei, ei.flip(0)], dim=1)
    print(f"[graph] kNN k={k}  directed_edges={ei.shape[1]}", flush=True)
    return ei


# ---------------------------------------------------------------- 评估
def evaluate(Z, slices, donors=None):
    """样本均值池化 → 审计三量 + donor 版 LODO tau。

    tau_ldo：leave-one-DONOR-out 岭探针（与审计论文 LODO AUC 同语义）。
    k>1 时 tau_lodo（切级 LOO，兄弟切片留在训练折）与 tau_ldo 之差
    = 切内可传递的 patient-block 成分——正是审计论文 LODO AUC 崩塌的
    修复侧度量。k=1 时两者语义重合（数值一致性检验）。"""
    rows, ys, names, ds = [], [], [], []
    for si, (nm, n0, n1) in enumerate(slices):
        sev = severity_of(nm)
        if sev is None:
            continue
        rows.append(Z[n0:n1].mean(axis=0))
        ys.append(sev)
        names.append(nm)
        ds.append(int(donors[n0].item()) if donors is not None else si)
    Xs = np.vstack(rows)
    y = np.asarray(ys, float)
    ds = np.asarray(ds)
    a = audit(Xs, y)
    tau_in = insample_tau(Xs, y)
    # sigma_null：同 seed 轻量置换（与 E1 完全一致的口径）
    H = operator(Xs)
    rng = np.random.default_rng(PERM_SEED)
    i, j = np.triu_indices(len(y), 1)
    taus = np.empty(2000)
    for st in range(0, 2000, 100):
        Y = np.stack([rng.permutation(y) for _ in range(100)])
        P = Y @ H.T
        aa = np.sign(P[:, j] - P[:, i])
        bb = np.sign(Y[:, j] - Y[:, i])
        den = np.sqrt((aa * aa).sum(1) * (bb * bb).sum(1))
        taus[st:st + 100] = np.divide((aa * bb).sum(1), den,
                                      out=np.zeros(len(P)), where=den > 0)
    sigma = float(taus.std(ddof=1))
    ldi = (a["tau"] - TAU_PERP) / sigma if sigma > 0 else float("inf")
    # leave-one-DONOR-out 岭探针（同款标准化+Ridge，donor 整块移出训练折）
    preds = np.zeros(len(y))
    for d in np.unique(ds):
        tr = ds != d
        te = ~tr
        if tr.sum() < 2 or te.sum() == 0:
            continue
        mu, sd = Xs[tr].mean(0), Xs[tr].std(0) + 1e-8
        Zt = (Xs[tr] - mu) / sd
        Ze = (Xs[te] - mu) / sd
        p = Zt.shape[1]
        w = np.linalg.solve(Zt.T @ Zt + np.eye(p), Zt.T @ y[tr])
        preds[te] = Ze @ w
    tau_ldo = float(kendall_tau(preds, y))
    return {"tau_lodo": a["tau"], "p_refit": a["p_refit"],
            "tau_insample": tau_in, "sigma_null": sigma, "ldi": ldi,
            "tau_ldo": tau_ldo, "n_samples": int(len(y)),
            "_Xs": Xs.tolist(), "_y": y.tolist(), "_names": list(names)}


# ---------------------------------------------------------------- 训练
def train_lambda(X, ei, patients, lam, args, device, labels=None):
    """lam 的语义随 --method 切换（对照臂设计，见方案 §12.2）：
      mrp       : loss = recon + lam * adv            （病人对抗，原方法）
      groupdro  : loss = Σ_g q_g L_g, q 指数梯度更新 η=lam（Sagawa 2020）
      irm       : loss = recon + lam * Σ_g ||∇_{1} R_g||²（IRMv1, Arjovsky 2019）
    三种方法的 λ=0 各自的"无去偏"基线；mrp 路径逐位不变以保既有结果可复现。"""
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    method = getattr(args, 'method', 'mrp')
    n_classes = 0
    if method == 'irm' and labels is not None:
        n_classes = int(labels.max().item()) + 1
    model = MethodB(X.shape[1], int(patients.max()) + 1,
                    hid=args.hid, out=args.dim, sn=args.adv_sn,
                    backbone=getattr(args, 'backbone', 'gat'),
                    n_classes=n_classes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    xd = (torch.from_numpy(X) if int(getattr(args, "recon_chunk", 0) or 0) > 0
          else torch.tensor(X, dtype=torch.float32, device=device))
    xd = xd.to(device)
    e = ei.to(device)
    pat = patients.to(device)
    yl = labels.to(device) if labels is not None else None
    n_don = int(patients.max().item()) + 1
    q = torch.full((n_don,), 1.0 / n_don, device=device)  # Group-DRO 组权重
    n = xd.shape[0]
    for ep in range(args.epochs):
        model.train()
        z = model.encode(xd, e)
        memtrace(f"ep{ep} after encode")
        chunk = int(getattr(args, "recon_chunk", 0) or 0)
        rec_spot = None
        dec = None
        if chunk > 0:
            # 分块解码：不物化 (n_spots x n_genes) 的 dec 及其梯度，
            # 峰值内存 ~chunk x n_genes；重建均值与原 F.mse_loss 等价。
            parts = []
            for i0 in range(0, z.shape[0], chunk):
                dz = model.dec(z[i0:i0 + chunk])
                parts.append((dz - xd[i0:i0 + chunk]).pow(2).mean(dim=1))
            rec_spot = torch.cat(parts)
            recon = rec_spot.mean()
        else:
            dec = model.dec(z)
            recon = F.mse_loss(dec, xd)
        memtrace(f"ep{ep} after recon")
        if method == 'mrp':
            # 稳定三件套之一：GRL warmup——前 args.warmup 个 epoch α=0，
            # 让编码器先收敛出可用表征再开对抗（避免早期梯度对抗打架）
            if ep < args.warmup:
                alpha = 0.0
            else:
                alpha = min(1.0, 2.0 * (ep - args.warmup)
                            / max(1, args.epochs - args.warmup)) * args.grl_cap
            zr = ReverseLayerF.apply(z, alpha)
            adv = F.cross_entropy(model.adv(zr), pat)
            loss = recon + lam * adv
            aux = adv.item()
        elif method == 'groupdro':
            # Group-DRO 臂：组=供者，最差供者的重建不被牺牲。
            # L_g = 供者 g 的 spot 平均重建损失；q ∝ q·exp(η·L_g)（η=lam），
            # loss = Σ_g q_g L_g。lam=0 → q 均匀 → 组均值重建（该臂自身基线）。
            rec_spot = ((dec - xd).pow(2).mean(dim=1) if rec_spot is None
                        else rec_spot)
            Lg = torch.zeros(n_don, device=device)
            cnt = torch.zeros(n_don, device=device)
            Lg = Lg.index_add(0, pat, rec_spot)
            cnt = cnt.index_add(0, pat, torch.ones_like(rec_spot))
            Lg = Lg / cnt.clamp_min(1.0)
            if lam > 0:
                q = q * torch.exp(lam * (Lg - Lg.max()).detach())
                q = q / q.sum().clamp_min(1e-12)
            loss = (q.detach() * Lg).sum()
            aux = float(Lg.max().item())
        elif method == 'irm':
            # IRMv1 臂：线性标签读出头在标量 w≡1 处的每供者风险梯度平方和，
            # 迫使"跨供者最优"的标签预测（不变性），而非记忆供者指纹。
            assert yl is not None, "method=irm 需要标签（--labels-from 或切片名）"
            loss = recon
            if lam > 0 and model.lhead is not None:
                scale = torch.ones(1, device=device, requires_grad=True)
                penal = torch.zeros((), device=device)
                for g in range(n_don):
                    m = pat == g
                    if int(m.sum()) < 2:
                        continue
                    risk = F.cross_entropy(model.lhead(z[m]) * scale, yl[m])
                    (gr,) = torch.autograd.grad(risk, scale, create_graph=True)
                    penal = penal + gr.pow(2)
                loss = recon + lam * penal / max(1, n_don)
                aux = float(penal.item())
        else:
            raise ValueError(f"unknown --method {method}")
        opt.zero_grad()
        loss.backward()
        # 稳定三件套之二：全局梯度裁剪（recon 尖峰 30-49 的直接抑制）
        if args.clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.clip)
        opt.step()
        memtrace(f"ep{ep} after step")
        if (ep + 1) % max(1, args.log_every) == 0:
            print(f"    ep{ep + 1:4d}  recon={recon.item():.4f}  "
                  f"aux={aux:.4f}  λ={lam}  method={method}", flush=True)
    model.eval()
    with torch.no_grad():
        Z = model.encode(xd, e).cpu().numpy()
    return Z, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="cohort root (cervix_all_ext)")
    ap.add_argument("--out", default="results/repair_e3_methodB.json")
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--n-genes", type=int, default=2000,
                    help="per-sample top-variance genes（train_st 同口径）")
    ap.add_argument("--k", type=int, default=6,
                    help="kNN neighbours per spot（train_st 同口径）")
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--hid", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--adv-list", type=float, nargs="*",
                    default=[0.0, 0.5, 1.0, 2.0, 5.0])
    ap.add_argument("--seeds", type=int, nargs="*", default=[0],
                    help="训练种子列表；判定用跨种子均值（方案要求）")
    ap.add_argument("--grl-cap", type=float, default=1.0)
    ap.add_argument("--warmup", type=int, default=0,
                    help="GRL warmup epochs（稳定三件套之一，0=off）")
    ap.add_argument("--clip", type=float, default=0.0,
                    help="global grad clip norm（稳定三件套之二，0=off）")
    ap.add_argument("--adv-sn", action="store_true",
                    help="spectral norm on adversary head（稳定三件套之三）")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--backbone", default="gat", choices=["gat", "gcn", "mlp"],
                    help="编码器骨干（E5 通用性消融：gat|gcn|mlp；"
                         "mlp=无消息传递的结构无关对照）")
    ap.add_argument("--method", default="mrp",
                    choices=["mrp", "groupdro", "irm"],
                    help="实验 A 对照臂（同一 GAT 骨干，仅换损失函数）："
                         "mrp=病人对抗（原方法，λ=对抗剂量）| "
                         "groupdro=供者组 DRO（λ=指数梯度步长 η）| "
                         "irm=跨供者不变性（λ=IRMv1 惩罚系数 β）"
                         "。三种方法的 λ=0 各自为无去偏基线。")
    ap.add_argument("--recon-chunk", type=int, default=0,
                    help=">0 时按该行数分块解码+重建（降低峰值内存；"
                         "0=off，默认路径逐位不变）。分组均值与原全量 "
                         "MSE 数学等价，仅浮点求和次序略有差异。")
    ap.add_argument("--dump-xs", action="store_true",
                    help="保存每次 run 的切片均值嵌入 Xs/y/names"
                         "（PERM 敏感性复核 + C3 基因方向分析材料）")
    ap.add_argument("--dump-w", default="",
                    help="保存解码器权重 npz 的路径（配合 --dump-lam）")
    ap.add_argument("--dump-lam", type=float, default=2.0,
                    help="保存解码器权重对应的 λ")
    ap.add_argument("--device", default="cuda:0")
    args = ap.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    X, coords, slices, panel = load_cohort(Path(args.data), args.n_genes)
    memtrace("after load_cohort")
    ei = build_edge_index(coords, k=args.k)
    memtrace("after build_edge_index")
    # 患者标签 = 从样本名解析的 donor ID（E2 相图：同 donor 多切片共享身份，
    # 对抗头才学得到「患者块」而非「切片块」。k=1 命名 CA_003 与切片编号
    # 一一对应，语义与 v1 按目录编号完全等价）
    import re as _re
    _DONOR_RE = _re.compile(r'((?:HPV[pn]|N|HSIL|CA)_[A-Za-z0-9]+)',
                            _re.IGNORECASE)

    def _donor_key(nm):
        m = _DONOR_RE.match(nm)
        return m.group(1).upper() if m else str(nm)

    _uniq = {}
    patients = np.zeros(X.shape[0], dtype=np.int64)
    for k, (nm, n0, n1) in enumerate(slices):
        dk = _donor_key(nm)
        patients[n0:n1] = _uniq.setdefault(dk, len(_uniq))
    n_donors = len(_uniq)
    print(f"[patients] {len(slices)} slices -> {n_donors} donors",
          flush=True)
    patients = torch.tensor(patients)
    # 实验 A：IRM 臂需要逐 spot 标签（severity_of 从切片名解析；未标注记 -1）
    labels = np.full(X.shape[0], -1, dtype=np.int64)
    for nm, n0, n1 in slices:
        sev = severity_of(nm)
        if sev is not None:
            labels[n0:n1] = int(sev)
    labels = torch.tensor(labels)
    print(f"[labels] {int((labels >= 0).sum())}/{len(labels)} spots labelled "
          f"(classes={sorted(set(labels[labels >= 0].tolist()))})", flush=True)

    report = {"params": vars(args), "n_spots": int(X.shape[0]),
              "n_genes_union": int(X.shape[1]), "n_donors": n_donors,
              "samples": [s[0] for s in slices], "scan": {}}
    for seed in args.seeds:
        for lam in args.adv_list:
            print(f"=== seed={seed}  lambda_adv={lam} ===", flush=True)
            t0 = time.time()
            args.seed = seed
            Z, model = train_lambda(X, ei, patients, lam, args, device,
                                    labels=labels)
            r = evaluate(Z, slices, patients)
            if getattr(args, "dump_xs", False):
                report.setdefault("dump_xs", {})[f"s{seed}_lam{lam}"] = {
                    "Xs": r.pop("_Xs"), "y": r.pop("_y"),
                    "names": r.pop("_names")}
            else:
                for kx in ("_Xs", "_y", "_names"):
                    r.pop(kx, None)
            if getattr(args, "dump_w", "") and seed == args.seeds[0] \
                    and abs(float(lam) - args.dump_lam) < 1e-9:
                np.savez(args.dump_w,
                         W=model.dec.weight.detach().cpu().numpy(),
                         panel=np.array(panel, dtype=object))
                print(f"  [dump-w] saved {args.dump_w}", flush=True)
            r["train_seconds"] = round(time.time() - t0, 1)
            print(f"  LDI={r['ldi']:+.3f}  tau_lodo={r['tau_lodo']:+.4f}  "
                  f"p_refit={r['p_refit']:.4f}  tau_in={r['tau_insample']:+.4f}  "
                  f"({r['train_seconds']}s)", flush=True)
            report["scan"][f"s{seed}_lam{lam}"] = r

    # ---- 判定（E1 修正口径：保真量 = LOO tau；跨种子均值）----
    def lam_mean(lam):
        rs = [r for k, r in report["scan"].items()
              if k.startswith("s") and k.endswith(f"_lam{lam}")]
        return (float(np.mean([r["ldi"] for r in rs])),
                float(np.mean([r["tau_lodo"] for r in rs])), len(rs))

    base_ldi, base_tau, n_base = lam_mean(0.0)
    passing = {}
    for lam in args.adv_list:
        if float(lam) <= 0:
            continue
        ml, mt, n = lam_mean(lam)
        report.setdefault("lam_means", {})[str(lam)] = {
            "mean_ldi": ml, "mean_tau_lodo": mt, "n_seeds": n}
        if n and n_base and ml < LDI_GATE and base_tau > 0 \
                and mt >= FIDELITY_KEEP * base_tau:
            passing[str(lam)] = {"mean_ldi": ml, "mean_tau_lodo": mt}
    verdict = {"E3": "go" if passing else "no-go",
               "base_mean_ldi": base_ldi, "base_mean_tau_lodo": base_tau,
               "passing_lambdas": list(passing),
               "gate": {"ldi": LDI_GATE, "fidelity_keep": FIDELITY_KEEP,
                        "fidelity_metric": "tau_lodo"}}
    report["verdict"] = verdict
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n==== E3 = {verdict['E3']} ==== "
          f"(passing λ={verdict['passing_lambdas']}; "
          f"base LDI={verdict['base_mean_ldi']:+.3f}, "
          f"tau_lodo={verdict['base_mean_tau_lodo']:+.4f})",
          flush=True)
    print(f"saved {args.out}", flush=True)


if __name__ == "__main__":
    main()
