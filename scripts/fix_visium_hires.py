# -*- coding: utf-8 -*-
"""为 GEO 下载的 Visium 样本补齐 spatial/tissue_hires_image.png

背景
----
src/st_data.py 识别标准 Visium 的硬性条件是同时存在：
    filtered_feature_bc_matrix.h5
    spatial/tissue_hires_image.png      <-- GEO 原始数据常常只有 lowres
    spatial/scalefactors_json.json
缺 hires 时会报 "No Visium (standard or HD) data found"。
本脚本从 spatial/image.tif（全分辨率）按 scalefactors_json.json 里的
tissue_hires_scalef 生成 hires PNG，使样本可被正常加载。

幂等：已存在 hires 则跳过。

用法
----
  python3 scripts/fix_visium_hires.py --dir data/st_visium/geo_crc_GSE280313
  python3 scripts/fix_visium_hires.py --dir data/st_visium/geo_crc_GSE280313 --force
"""
import argparse
import glob
import json
import os

from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # 全分辨率 WSIs 可能很大


def build_one(sample_dir, force=False):
    sp = os.path.join(sample_dir, "spatial")
    hires = os.path.join(sp, "tissue_hires_image.png")
    if os.path.exists(hires) and not force:
        return "skip"
    sf_path = os.path.join(sp, "scalefactors_json.json")
    tif = os.path.join(sp, "image.tif")
    if not os.path.exists(sf_path):
        return "no_scalefactors"
    if not os.path.exists(tif):
        return "no_tif"
    with open(sf_path) as f:
        sf = json.load(f)
    im = Image.open(tif)
    W, H = im.size
    scale = sf.get("tissue_hires_scalef")
    if not scale:
        # 兜底：让 hires 长边约 2000 px（标准 Visium hires 量级）
        scale = 2000.0 / max(W, H)
    tw, th = max(1, int(round(W * scale))), max(1, int(round(H * scale)))
    im.resize((tw, th), Image.LANCZOS).save(hires, "PNG")
    return f"{W}x{H} -> {tw}x{th}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="含 GSM*/ 样本子目录的根目录")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    samples = sorted(glob.glob(os.path.join(args.dir, "*/")))
    if not samples:
        print(f"[WARN] {args.dir} 下没有样本子目录")
        return 0
    for sd in samples:
        lab = os.path.basename(sd.rstrip("/"))
        try:
            r = build_one(sd, args.force)
        except Exception as e:
            print(f"  {lab:26s} FAIL  {type(e).__name__}: {e}")
            continue
        if r == "skip":
            print(f"  {lab:26s} hires 已存在，跳过")
        elif r.startswith("no_"):
            print(f"  {lab:26s} 跳过（{r}）")
        else:
            print(f"  {lab:26s} 已生成 hires  {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
