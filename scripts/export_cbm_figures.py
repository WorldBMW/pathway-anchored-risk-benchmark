# -*- coding: utf-8 -*-
"""export_cbm_figures.py — 按 Elsevier / Computers in Biology and Medicine 图像规范导出投稿用图。

期刊技术要求（Elsevier artwork guidelines）：
  - 混合图（线条 + 半色调，本工作全部为混合图）：≥500 dpi
  - 纯线条图：≥1000 dpi；半色调照片：≥300 dpi
  - 首选格式 TIFF（LZW 压缩）、RGB；同时保留 PNG
  - 版面：单栏约 90 mm，双栏约 190 mm；打印宽度不得超过 190 mm

输入 : papers/07_CSBJ_v10/Figures/Fig*.png（由 scripts/gen_figures_v10.py 生成）
输出 : papers/11_CiBM/figures/*.png 与 *.tif（500 dpi；如像素过宽则下采样到 ≤190 mm）

用法 : python scripts/export_cbm_figures.py
"""
import glob
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "papers", "07_CSBJ_v10", "Figures")
DST = os.path.join(ROOT, "papers", "11_CiBM", "figures")

DPI = 500                    # 混合图最低要求
MAX_W_IN = 190 / 25.4        # 190 mm 双栏最大打印宽度

FIGS = [
    "Fig1_Framework.png",
    "Fig2_risk_violin.png",
    "Fig3_ablation_multiseed.png",
    "Fig4_biology_correlation.png",
    "Fig5_external_transfer.png",
]


def main():
    os.makedirs(DST, exist_ok=True)
    max_px = int(round(MAX_W_IN * DPI))
    for name in FIGS:
        src = os.path.join(SRC, name)
        if not os.path.exists(src):
            print("  [warn] missing", name)
            continue
        im = Image.open(src).convert("RGB")
        w0, h0 = im.size
        if w0 > max_px:
            nh = int(round(h0 * max_px / w0))
            im = im.resize((max_px, nh), Image.LANCZOS)
        im.save(os.path.join(DST, name), dpi=(DPI, DPI))
        tif = os.path.splitext(name)[0] + ".tif"
        im.save(os.path.join(DST, tif), format="TIFF",
                compression="tiff_lzw", dpi=(DPI, DPI))
        w, h = im.size
        print(f"  {name}: {w0}x{h0} -> {w}x{h} px @ {DPI} dpi "
              f"(print {w / DPI * 25.4:.0f}x{h / DPI * 25.4:.0f} mm)")
    print("done ->", DST)


if __name__ == "__main__":
    main()