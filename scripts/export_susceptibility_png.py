"""
Export a clean, axis-free probability raster PNG for the dashboard BitmapLayer.

Reads outputs/susceptibility.tif (Band 1 = probability),
applies RdYlGn_r colormap (vmin=0, vmax=1),
sets nodata pixels to alpha=0,
writes dashboard/public/data/susceptibility.png at native 802x1101 resolution.

Run once:
    conda activate py311_ds
    python scripts/export_susceptibility_png.py
"""

from pathlib import Path
import numpy as np
import rasterio
import matplotlib.cm as cm
from PIL import Image

OUTPUTS = Path(__file__).parent.parent / "outputs"
OUT_PNG = Path(__file__).parent.parent / "dashboard" / "public" / "data" / "susceptibility.png"

with rasterio.open(OUTPUTS / "susceptibility.tif") as src:
    prob = src.read(1)          # float32, nodata=nan
    nodata = src.nodata         # should be nan

nodata_mask = np.isnan(prob)

# Normalize and apply colormap
norm = np.clip(prob, 0, 1)
colormap = cm.get_cmap("RdYlGn_r")
rgba = colormap(norm)           # (H, W, 4) float [0,1]

# Zero-out alpha where nodata
rgba[nodata_mask, 3] = 0.0

# Convert to uint8
img_array = (rgba * 255).astype(np.uint8)
img = Image.fromarray(img_array, mode="RGBA")

OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT_PNG, "PNG", optimize=True)

size_kb = OUT_PNG.stat().st_size / 1024
print(f"Saved {OUT_PNG}")
print(f"  Size:  {size_kb:.0f} KB")
print(f"  Shape: {img.width} x {img.height} px")
print(f"  Nodata pixels masked: {nodata_mask.sum():,}")
