"""
export_dashboard_data.py
------------------------
Produces all static assets for the Next.js dashboard.
Run from project root:
    conda activate py311_ds
    python src/maps/export_dashboard_data.py

Outputs go to dashboard/public/data/ (9 files).
"""

import json
import struct
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy as rasterio_xy

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dashboard" / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)

print(f"Output directory: {OUT}")

# ---------------------------------------------------------------------------
# 1. Grid binary (grid.bin + grid_meta.json)
# ---------------------------------------------------------------------------
print("\n[1/6] Encoding susceptibility grid → grid.bin ...")

with rasterio.open(ROOT / "outputs" / "susceptibility.tif") as src:
    prob_band = src.read(1)   # float32 probabilities
    class_band = src.read(2)  # float32 classes 1–4
    transform = src.transform
    shape = src.shape         # (rows, cols) = (1101, 802)

# Find valid (non-NaN) cells
valid_mask = ~np.isnan(prob_band)
rows, cols = np.where(valid_mask)

# Get geographic coordinates
lons_arr, lats_arr = rasterio_xy(transform, rows, cols)
lons_arr = np.array(lons_arr, dtype=np.float64)
lats_arr = np.array(lats_arr, dtype=np.float64)
probs_arr = prob_band[valid_mask].astype(np.float64)
classes_arr = class_band[valid_mask].astype(np.uint8)

# Quantise to uint16 offsets for compact encoding
LON_MIN = float(lons_arr.min())
LON_MAX = float(lons_arr.max())
LAT_MIN = float(lats_arr.min())
LAT_MAX = float(lats_arr.max())

lon_u16 = np.round((lons_arr - LON_MIN) / (LON_MAX - LON_MIN) * 65535).astype(np.uint16)
lat_u16 = np.round((lats_arr - LAT_MIN) / (LAT_MAX - LAT_MIN) * 65535).astype(np.uint16)
prob_u16 = np.round(probs_arr * 65535).astype(np.uint16)

# Write as packed struct array: [u16 lon][u16 lat][u16 prob][u8 class] = 7 bytes/point
# Use numpy structured array for fast binary serialisation
n_points = len(lon_u16)
dt = np.dtype([('lon', '<u2'), ('lat', '<u2'), ('prob', '<u2'), ('cls', 'u1')])
grid_arr = np.empty(n_points, dtype=dt)
grid_arr['lon'] = lon_u16
grid_arr['lat'] = lat_u16
grid_arr['prob'] = prob_u16
grid_arr['cls'] = classes_arr

with open(OUT / "grid.bin", "wb") as f:
    f.write(grid_arr.tobytes())

# Compute class counts → area (each cell ~500m × 500m = 0.25 km²)
CELL_AREA_KM2 = 0.25
class_counts = {int(c): int((classes_arr == c).sum()) for c in [1, 2, 3, 4]}
area_km2 = {c: round(count * CELL_AREA_KM2) for c, count in class_counts.items()}

# Jenks thresholds from band2 class boundaries
# class 1→prob range, etc. — compute from actual probabilities
class_labels = {1: "Low", 2: "Moderate", 3: "High", 4: "Very High"}
thresholds = {}
for cls in [1, 2, 3, 4]:
    mask = classes_arr == cls
    if mask.any():
        thresholds[cls] = {
            "min": round(float(probs_arr[mask].min()), 4),
            "max": round(float(probs_arr[mask].max()), 4),
        }

grid_meta = {
    "n_points": n_points,
    "lon_min": LON_MIN,
    "lon_max": LON_MAX,
    "lat_min": LAT_MIN,
    "lat_max": LAT_MAX,
    "class_labels": class_labels,
    "class_thresholds": thresholds,
    "area_km2": {class_labels[c]: area_km2[c] for c in [1, 2, 3, 4]},
    "cell_area_km2": CELL_AREA_KM2,
}
with open(OUT / "grid_meta.json", "w") as f:
    json.dump(grid_meta, f, indent=2)

print(f"  → {n_points:,} points written ({(OUT / 'grid.bin').stat().st_size / 1e6:.1f} MB)")
print(f"  → Area: {area_km2}")

# ---------------------------------------------------------------------------
# 2. Fire binary (fires.bin + fires_meta.json)
# ---------------------------------------------------------------------------
print("\n[2/6] Encoding fire detections → fires.bin ...")

modis = gpd.read_file(ROOT / "data" / "processed" / "firms_modis.gpkg")
viirs = gpd.read_file(ROOT / "data" / "processed" / "firms_viirs.gpkg")

# Ensure date is datetime
modis["date"] = pd.to_datetime(modis["date"])
viirs["date"] = pd.to_datetime(viirs["date"])

# Build combined array: [f32 lon, f32 lat, u8 year_off, u8 month]
def encode_fires(df: pd.DataFrame) -> bytes:
    """Encode fire points as [f32 lon][f32 lat][u8 year_off][u8 month] = 10 bytes/point."""
    dt = np.dtype([('lon', '<f4'), ('lat', '<f4'), ('year_off', 'u1'), ('month', 'u1')])
    arr = np.empty(len(df), dtype=dt)
    arr['lon'] = df["lon"].values.astype(np.float32)
    arr['lat'] = df["lat"].values.astype(np.float32)
    arr['year_off'] = (df["date"].dt.year - 2000).values.astype(np.uint8)
    arr['month'] = df["date"].dt.month.values.astype(np.uint8)
    return arr.tobytes()

modis_bytes = encode_fires(modis)
viirs_bytes = encode_fires(viirs)

with open(OUT / "fires.bin", "wb") as f:
    f.write(modis_bytes)
    f.write(viirs_bytes)

fires_meta = {
    "n_modis": len(modis),
    "n_viirs": len(viirs),
    "n_total": len(modis) + len(viirs),
    "modis_period": "2001-2022",
    "viirs_period": "2023-2024",
    "year_min": 2000,
    "year_max": 2024,
    "bytes_per_record": 10,
    "format": "[f32 lon][f32 lat][u8 year_off][u8 month]",
}
with open(OUT / "fires_meta.json", "w") as f:
    json.dump(fires_meta, f, indent=2)

print(f"  → {len(modis):,} MODIS + {len(viirs):,} VIIRS = {len(modis)+len(viirs):,} total fires")
print(f"  → {(OUT / 'fires.bin').stat().st_size / 1e3:.0f} KB")

# ---------------------------------------------------------------------------
# 3. Annual fire timeline (annual_fires.json)
# ---------------------------------------------------------------------------
print("\n[3/6] Building annual fire timeline → annual_fires.json ...")

modis["source"] = "MODIS"
viirs["source"] = "VIIRS"
all_fires = pd.concat([modis[["date", "source"]], viirs[["date", "source"]]], ignore_index=True)
all_fires["year"] = all_fires["date"].dt.year

annual = (
    all_fires.groupby(["year", "source"])
    .size()
    .reset_index(name="count")
    .sort_values("year")
)
annual_list = annual.rename(columns={"year": "year", "source": "source", "count": "count"}).to_dict(orient="records")
# Ensure int types for JSON
for row in annual_list:
    row["year"] = int(row["year"])
    row["count"] = int(row["count"])

with open(OUT / "annual_fires.json", "w") as f:
    json.dump(annual_list, f, indent=2)

print(f"  → {len(annual_list)} year-source entries, {all_fires['year'].min()}–{all_fires['year'].max()}")

# ---------------------------------------------------------------------------
# 4. Simplified risk zones GeoJSON (zones_simplified.geojson)
# ---------------------------------------------------------------------------
print("\n[4/6] Simplifying risk zones → zones_simplified.geojson ...")

zones = gpd.read_file(ROOT / "outputs" / "susceptibility_zones.geojson")
zones_simp = zones.copy()
zones_simp["geometry"] = zones_simp.geometry.simplify(tolerance=0.01, preserve_topology=True)
zones_simp.to_file(OUT / "zones_simplified.geojson", driver="GeoJSON")

orig_mb = (ROOT / "outputs" / "susceptibility_zones.geojson").stat().st_size / 1e6
simp_mb = (OUT / "zones_simplified.geojson").stat().st_size / 1e6
print(f"  → {orig_mb:.1f} MB → {simp_mb:.1f} MB (tolerance=0.01°)")

# ---------------------------------------------------------------------------
# 5. SHAP global importance (shap_global.json)
# ---------------------------------------------------------------------------
print("\n[5/6] Exporting SHAP data ...")

shap_summary = json.load(open(ROOT / "outputs" / "shap_summary_v2.json"))
# Convert dict to sorted list [{feature, mean_abs_shap}]
shap_global = [
    {"feature": k, "mean_abs_shap": round(v, 6)}
    for k, v in sorted(shap_summary.items(), key=lambda x: -x[1])
]
with open(OUT / "shap_global.json", "w") as f:
    json.dump(shap_global, f, indent=2)
print(f"  → shap_global.json: {len(shap_global)} features")

# SHAP samples: 100 fire + 100 no-fire from test CSV
shap_df = pd.read_csv(ROOT / "outputs" / "shap" / "shap_values_test_v2.csv")
feat_cols = [c for c in shap_df.columns if c not in ["label", "pred_prob"]]

fire_sample = shap_df[shap_df["label"] == 1].sample(
    min(100, (shap_df["label"] == 1).sum()), random_state=42
)
nofire_sample = shap_df[shap_df["label"] == 0].sample(
    min(100, (shap_df["label"] == 0).sum()), random_state=42
)
samples = pd.concat([fire_sample, nofire_sample], ignore_index=True)
# Round floats for smaller JSON
for col in feat_cols:
    samples[col] = samples[col].round(5)
samples["pred_prob"] = samples["pred_prob"].round(4)

samples.to_json(OUT / "shap_samples.json", orient="records", indent=2)
print(f"  → shap_samples.json: {len(samples)} samples × {len(feat_cols)} SHAP features")

# ---------------------------------------------------------------------------
# 6. Merged stats JSON (stats.json)
# ---------------------------------------------------------------------------
print("\n[6/6] Building stats.json ...")

validation = json.load(open(ROOT / "outputs" / "validation_stats.json"))
models_raw = json.load(open(ROOT / "outputs" / "v2_tuned_metrics.json"))

# Clean model metrics for dashboard (drop internal fields)
models = []
for m in models_raw:
    models.append({
        "model": m["model"],
        "cv_auc": round(m["cv_auc_best"], 4),
        "test_auc": round(m["test_roc_auc"], 4),
        "test_accuracy": round(m["test_accuracy"], 4),
        "test_precision": round(m["test_precision"], 4),
        "test_recall": round(m["test_recall"], 4),
        "test_f1": round(m["test_f1"], 4),
    })

stats = {
    "validation": validation,
    "models": models,
    "area_km2": {class_labels[c]: area_km2[c] for c in [1, 2, 3, 4]},
    "total_area_km2": sum(area_km2.values()),
    "province": "Córdoba, Argentina",
    "training_period": "2001–2022 (MODIS)",
    "validation_period": "2023–2024 (VIIRS)",
    "n_grid_cells": n_points,
    "grid_resolution_m": 500,
}
with open(OUT / "stats.json", "w") as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)
print(f"  → stats.json written")

# ---------------------------------------------------------------------------
# Copy ROC curve image to public/data
# ---------------------------------------------------------------------------
import shutil
roc_src = ROOT / "outputs" / "v2_roc_curves_final.png"
roc_dst = OUT / "roc_curves.png"
shutil.copy2(roc_src, roc_dst)
print(f"\n  → Copied ROC curve image ({roc_dst.stat().st_size / 1e3:.0f} KB)")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("Export complete. Files in dashboard/public/data/:")
for p in sorted(OUT.iterdir()):
    print(f"  {p.name:35s} {p.stat().st_size / 1e3:8.1f} KB")
print("=" * 60)
