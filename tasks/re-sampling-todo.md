# Plan: Fix Geographic Confounding in Sampling & Modeling

## Context

The baseline models achieve AUC ~0.997, which is suspiciously high. The root cause is **geographic confounding in the negative sampling**:

- Fires cluster in the Sierras de Córdoba (NW-W of province, elevation ~300-2800m)
- The 5km exclusion buffer in `sampling.py` pushes ALL negatives out of the mountain zone into the flat eastern plains
- Land cover stratification doesn't fix this — same LC classes exist at different elevations
- Models learn "mountains = fire, plains = no fire" using elevation, slope, clay, distance features
- The resulting susceptibility map would trivially paint the Sierras red and everything else green

**Goal:** Fix sampling so models learn *within-terrain* fire drivers (vegetation, climate, anthropogenic conditions) rather than *between-terrain* geographic separation. Expected AUC after fix: 0.75-0.90 (matching literature benchmarks for proper spatial CV).

---

## Step 1: Notebook `03a_resampling.ipynb` — Elevation-Stratified Resampling

**Core change:** Generate negatives that span the same elevation distribution as fire points, forcing the model to learn what *within* mountainous terrain makes a location fire-prone.

Cells:
1. Load fire points (`firms_modis.gpkg`) + DEM raster (`data/raw/dem/elevation.tif`). Extract elevation at each fire point. Plot fire-point elevation histogram.
2. Define 5 elevation bands from fire-point distribution (quantile-based, e.g. 0-200m, 200-400m, 400-700m, 700-1200m, >1200m — refine from data).
3. Compute **joint strata: elevation_band x land_cover_class**. For each fire point, assign stratum. Compute fire count per stratum (this becomes the negative target distribution).
4. Generate negatives with **joint stratification**:
   - Reuse the rejection-sampling loop from `sampling.py` (cKDTree, boundary check)
   - **Reduce buffer from 5km to 1km** — 5km is too aggressive for a ~50-80km wide mountain corridor; 1km still avoids the same 500m MODIS pixel
   - For each candidate, read elevation from DEM + land cover from raster → assign stratum
   - Accept/reject based on stratum quotas (proportional to fire distribution per stratum)
5. Diagnostic plots:
   - Elevation histograms: old negatives vs new negatives vs fire points (new should overlap with fires)
   - Spatial scatter: new negatives should appear in the Sierras, not just plains
   - Boxplots of key confounders (elevation, slope, clay, distance_to_road): old vs new
6. Save `data/processed/sample_points_v2.gpkg`
7. Re-extract features using same pipeline as `extract_features.py` + `compute_osm_distances.py` → save `data/processed/dataset_v2.csv`

**Key files to reuse:**
- `data/processing/sampling.py` — cKDTree exclusion, boundary check, LC reading functions (`load_boundary`, `load_all_fire_points_utm`, `read_lc_at_points`, dedup logic)
- `data/processing/extract_features.py` — raster extraction at points
- `data/processing/compute_osm_distances.py` — OSM distance computations
- `data/raw/dem/elevation.tif` — for elevation at candidate points

---

## Step 2: Notebook `03b_preprocessing_v2.ipynb` — Preprocessing with Spatial CV

**Must redo from scratch** because the dataset changes (different negatives → different distributions → different VIF/scaling).

Pipeline:
1. Load `dataset_v2.csv`, impute `population_density` NaN with median
2. **Assign spatial block IDs**: convert (lat, lon) to UTM 20S, integer-divide by 20km → block_id. Store as column.
3. Iterative VIF filter (threshold=10) — re-run; results may differ
4. Pairwise correlation filter (|r| > 0.85)
5. One-hot encode `land_cover_class`
6. **Spatial block train/test split**: `GroupShuffleSplit(test_size=0.30)` with block_id as groups (no block in both train and test)
7. `StandardScaler` fit on train only, transform both
8. Save: `train_v2.csv`, `test_v2.csv`, `scaler_v2.pkl`, `encoder_v2.pkl`, `selected_features_v2.json`

---

## Step 3: Notebook `04_modeling_v2.ipynb` — Baseline Models with Spatial CV

Same 3 models (RF, XGBoost, LightGBM) but with:
- **`GroupKFold(n_splits=5)`** using spatial block IDs instead of `StratifiedKFold(n_splits=10)`
- Holdout test = spatially separate blocks (from step 2)
- Log to MLflow, save comparison table, ROC curves, confusion matrices
- **Compare v1 vs v2**: show the AUC drop as evidence of confounding (useful for the paper)

---

## Step 4: Verification

- [ ] Elevation KS-test: fire vs new-negatives distribution p-value > 0.05 (overlap)
- [ ] Spatial plot shows negatives in mountain zone (not just plains)
- [ ] Spatial CV AUC drops significantly vs random CV (expected: 0.75-0.90)
- [ ] Feature importances shift: elevation/slope less dominant, vegetation/climate/anthropogenic features rise
- [ ] No block leaks between train/test (check block_id intersection is empty)
- [ ] AUC > 0.65 (below this → over-corrected, investigate band granularity)

---

## Config Updates (`configs/cordoba.yaml`)

```yaml
sampling:
  negative_buffer_km: 1          # Reduced from 5
  stratify_by: ["land_cover_class", "elevation_band"]
  elevation_bands: "quantile"    # Determined from fire-point distribution
  
spatial_cv:
  block_size_km: 20
  n_folds: 5
```

---

## Execution Order

```
03a_resampling.ipynb  →  sample_points_v2.gpkg + dataset_v2.csv
       ↓
03b_preprocessing_v2.ipynb  →  train_v2.csv + test_v2.csv
       ↓
04_modeling_v2.ipynb  →  spatial CV baselines + v1 vs v2 comparison
```
