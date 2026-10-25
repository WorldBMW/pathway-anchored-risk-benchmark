# -*- coding: utf-8 -*-
"""
gen_fig1_histology_v10.py
------------------------------------------------------------------------------
Composite Figure 1 for the cervix ST manuscript (CMPB, Q2 target):

  panel (a)  REAL H&E histologic spectrum of the cervical Visium cohort
             normal ectocervix | HSIL (CIN) | invasive SCC | invasive ADC
             top row: whole-section low-power H&E (Visium capture frame)
             bottom row: high-power crop of the boxed diagnostic region
             sources: P020 (GSE217237); HSIL_HPV/CA_HPV_2 (GSE208654);
             cervical_cancer_1 (public 10x Genomics FFPE demo section)
  panel (b)  framework schematic (asset Fig1b_schematic.png, 600 dpi,
             produced by gen_fig1_framework.py)

Run order:  python gen_fig1_framework.py   (makes Fig1b_schematic)
            python gen_fig1_histology_v10.py  (this script -> Fig1_Framework)

SCIENTIFIC GUARDRAILS (why the figure looks like this)
------------------------------------------------------------------------------
* NO model output / risk score is overlaid on H&E.  Quantitative QC (spot vs
  H&E morphology: risk r=-0.18 with nuclear density, only 47% of top-5% spots
  on tissue; slide-level capture-array offsets in the four GSE208654 disease
  sections) showed per-spot scores do not register to histologic morphology,
  so an overlay would mislead.  H&E is shown as histologic CONTEXT ONLY, which
  the caption states explicitly.
* Every high-power crop was morphology-verified:
  P020      orderly stratified squamous epithelium with surface maturation
  HSIL_HPV  thickened, disorganized squamous epithelium (full-thickness atypia)
  CC1       infiltrating tumor nests/cords in desmoplastic stroma (SCC)
  CA_HPV_2  back-to-back / cribriform malignant glands (endocervical ADC)
* Whole-section tiles are tissue-bbox cropped from the original H&E (no warp);
  high-power tiles use identical cover-fit cropping; a mild per-channel
  percentile white-balance (0.8/99.2) is display-only and applied identically.

Output: papers/07_CSBJ_v10/Figures/Fig1_Framework.{png,pdf}  (300 dpi)
------------------------------------------------------------------------------
"""
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "papers" / "07_CSBJ_v10" / "Figures"
F_ARIAL = "C:/Windows/Fonts/arial.ttf"
F_ARIALBD = "C:/Windows/Fonts/arialbd.ttf"

# ---- composite geometry (px, 300 dpi; width 7.4 in = 2220) ----
W = 2220
ML, MR, GAP = 58, 30, 24
COL_W = (W - ML - MR - 3 * GAP) // 4          # 515
TITLE_H = 78
THUMB_Y, THUMB_H = 6, 440                     # within band (after title)
INS_Y, INS_H = 460, 320
BAND_H = TITLE_H + THUMB_Y + THUMB_H + 12 + INS_H + 16   # 872
GUTTER = 30

# (key, image path, title, source, high-power box in full-image norm coords,
#  optional (lo,hi) white-balance percentiles)
CASES = [
    ("P020",
     ROOT / "data/st_visium/geo_ectocervix/P020/spatial/tissue_hires_image.png",
     "Normal ectocervix", "GSE217237 · P020",
     (0.30, 0.090, 0.62, 0.290), None),
    ("HSIL",
     ROOT / "data/st_visium/geo_cesc/HSIL_HPV/spatial/tissue_hires_image.png",
     "HSIL (CIN2–3)", "GSE208654 · HSIL_HPV",
     (0.25, 0.275, 0.51, 0.435), None),
    ("SCC",
     ROOT / "data/st_visium/cervical_cancer_1/image.jpg",
     "Invasive squamous-cell carcinoma", "10x FFPE · cervical_cancer_1",
     (0.52, 0.400, 0.745, 0.540), (0.004, 0.996)),
    ("ADC",
     ROOT / "data/st_visium/geo_cesc/CA_HPV_2/spatial/tissue_hires_image.png",
     "Invasive adenocarcinoma", "GSE208654 · CA_HPV_2",
     (0.33, 0.170, 0.575, 0.322), None),
]


def load_rgb(p: Path) -> np.ndarray:
    im = Image.open(p).convert("RGB")
    return np.asarray(im)


def white_balance(a: np.ndarray, lo_q=0.008, hi_q=0.992) -> np.ndarray:
    """Mild per-channel percentile stretch (display only)."""
    small = a[::max(1, a.shape[0] // 600), ::max(1, a.shape[1] // 600)]
    out = np.empty_like(a, dtype=np.float32)
    for ch in range(3):
        lo, hi = np.quantile(small[:, :, ch], [lo_q, hi_q])
        out[:, :, ch] = np.clip((a[:, :, ch].astype(np.float32) - lo) /
                                (hi - lo + 1e-6), 0, 1) * 255.0
    return out.astype(np.uint8)


def tissue_bbox(a: np.ndarray, pad=0.03):
    """Tissue bbox in full-image normalized coords (luminance mask, downscaled)."""
    h, w = a.shape[:2]
    sc = 700.0 / max(h, w)
    small = np.asarray(Image.fromarray(a).resize(
        (max(2, int(w * sc)), max(2, int(h * sc))), Image.BILINEAR))
    lum = 0.299 * small[:, :, 0] + 0.587 * small[:, :, 1] + 0.114 * small[:, :, 2]
    ys, xs = np.where(lum < 230)
    if len(xs) == 0:
        return (0.0, 0.0, 1.0, 1.0)
    x0, x1 = xs.min() / small.shape[1], xs.max() / small.shape[1]
    y0, y1 = ys.min() / small.shape[0], ys.max() / small.shape[0]
    dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
    return (max(0.0, x0 - dx), max(0.0, y0 - dy),
            min(1.0, x1 + dx), min(1.0, y1 + dy))


def cover_tile(a: np.ndarray, box, tw: int, th: int):
    """Crop normalized box -> cover-fit resize to (tw,th); returns tile +
    the source crop rect (norm of full image) actually displayed."""
    H, Wd = a.shape[:2]
    x0, y0, x1, y1 = box
    cx0, cy0, cx1, cy1 = int(x0 * Wd), int(y0 * H), int(x1 * Wd), int(y1 * H)
    crop = a[cy0:cy1, cx0:cx1]
    ch, cw = crop.shape[:2]
    s = max(tw / cw, th / ch)
    rw, rh = int(round(cw * s)), int(round(ch * s))
    r = np.asarray(Image.fromarray(crop).resize((rw, rh), Image.LANCZOS))
    # center crop
    yA = max(0, (rh - th) // 2)
    xA = max(0, (rw - tw) // 2)
    tile = r[yA:yA + th, xA:xA + tw]
    # displayed source rect in full-image norm coords
    sx0 = x0 + (xA / s) / Wd
    sy0 = y0 + (yA / s) / H
    sx1 = sx0 + tw / s / Wd
    sy1 = sy0 + th / s / H
    return tile, (sx0, sy0, sx1, sy1)


def panel_a() -> Image.Image:
    band = Image.new("RGB", (W, BAND_H), "white")
    dr = ImageDraw.Draw(band)
    f_title = ImageFont.truetype(F_ARIALBD, 25)
    f_src = ImageFont.truetype(F_ARIAL, 17)

    for ci, (key, img_p, title, src, hi_box, wb) in enumerate(CASES):
        xL = ML + ci * (COL_W + GAP)
        a = white_balance(load_rgb(img_p),
                          *(wb if wb is not None else (0.008, 0.992)))
        bb = tissue_bbox(a)

        # ---- whole-section thumbnail (tissue bbox, cover fit) ----
        thumb, disp = cover_tile(a, bb, COL_W, THUMB_H)
        band.paste(Image.fromarray(thumb), (xL, TITLE_H + THUMB_Y))

        # inset-location rectangle: hi_box (full-image norm) -> thumbnail px
        bx0, by0, bx1, by1 = bb
        sx0, sy0, sx1, sy1 = disp
        def to_tile(qx, qy):
            fx = (qx - sx0) / (sx1 - sx0) * COL_W
            fy = (qy - sy0) / (sy1 - sy0) * THUMB_H
            return xL + fx, TITLE_H + THUMB_Y + fy
        ix0, iy0 = to_tile(hi_box[0], hi_box[1])
        ix1, iy1 = to_tile(hi_box[2], hi_box[3])
        rw, rh = ix1 - ix0, iy1 - iy0
        if rw > 6 and rh > 6:                      # white halo + black box
            dr.rectangle([ix0 - 3, iy0 - 3, ix1 + 3, iy1 + 3],
                         outline=(255, 255, 255), width=7)
            dr.rectangle([ix0, iy0, ix1, iy1], outline=(20, 20, 20), width=3)

        # ---- high-power inset ----
        ins, _ = cover_tile(a, hi_box, COL_W, INS_H)
        iy = TITLE_H + INS_Y
        band.paste(Image.fromarray(ins), (xL, iy))
        dr.rectangle([xL, iy, xL + COL_W - 1, iy + INS_H - 1],
                     outline=(20, 20, 20), width=3)

        # ---- column text ----
        def ctext(y, fnt, txt, fill):
            tw = dr.textlength(txt, font=fnt)
            dr.text((xL + (COL_W - tw) / 2, y), txt, font=fnt, fill=fill)
        ctext(2, f_title, title, (27, 27, 27))
        ctext(38, f_src, src, (90, 90, 90))

    return band


def main():
    band = panel_a()
    sch = Image.open(FIG / "Fig1b_schematic.png").convert("RGB")
    sch = sch.resize((W, round(sch.height * W / sch.width)), Image.LANCZOS)

    H_total = BAND_H + GUTTER + sch.height
    canvas = Image.new("RGB", (W, H_total), "white")
    canvas.paste(band, (0, 0))
    canvas.paste(sch, (0, BAND_H + GUTTER))

    dr = ImageDraw.Draw(canvas)
    f_letter = ImageFont.truetype(F_ARIALBD, 52)
    dr.text((10, 2), "a", font=f_letter, fill=(20, 20, 20))
    dr.text((10, BAND_H + GUTTER - 2), "b", font=f_letter, fill=(20, 20, 20))

    FIG.mkdir(parents=True, exist_ok=True)
    png = FIG / "Fig1_Framework.png"
    pdf = FIG / "Fig1_Framework.pdf"
    canvas.save(png, dpi=(300, 300))
    canvas.save(pdf, "PDF", resolution=300.0)
    print(f"saved {png}  ({canvas.size[0]}x{canvas.size[1]} px @300dpi)")
    print(f"saved {pdf}")


if __name__ == "__main__":
    main()
