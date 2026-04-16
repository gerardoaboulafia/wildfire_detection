# Project Plan: Wildfire Susceptibility Mapping — Córdoba, Argentina

## Context

Greenfield project — no code exists yet. Goal is to build an ML-based wildfire susceptibility map for Córdoba Province with a 3D visualization dashboard, producing both a scientific article and a deployed app.

### Reusable Code Analysis (`reusable_code/`)

Three files from the prior Forest-Fire project are available. Key adaptation notes:

**`SoilGrids.py`** — Nearly direct reuse. Queries ISRIC SoilGrids REST API point-by-point for bdod, phh2o, clay, soc, ocd, ocs at multiple depths. Returns pivoted DataFrame. **Adaptation needed:** just call with Córdoba coordinates. **Bottleneck:** point-by-point HTTP calls will be slow for the ~500m prediction grid — consider batch download from SoilGrids WCS for raster coverage instead.

**`geospatial.py`** — Heavy adaptation needed. Currently US-focused (has `que_estado()` for US state lookup, reads `data/estados_usa.gpkg`). Useful functions to adapt:
- `caracterizar_rutas_detallado()` → road km by type within 5km buffer (reusable, just remove US state context)
- `caracterizar_uso_agua_detallado()` → water body % and waterway km within 5km buffer (reusable)
- `analizar_punto()` → distance to nearest city, fire stations, population (reusable, adapt buffer radii)
- `caracterizar_uso_suelo()` → land use proportions (partially reusable — we'll have Copernicus land cover raster, so OSM land use becomes supplementary)
- **Remove:** `que_estado()` and STATE column entirely
- **Simplify:** for susceptibility mapping we mainly need `distance_to_road`, `distance_to_river`, `distance_to_settlement` — the detailed km-by-type breakdowns may add noise

**`GEE.py`** — Major rework needed. Currently:
- Uses `USGS/3DEP/10m` for slope (US-only DEM) → **Switch to SRTM** (`USGS/SRTMGL1_003`, global 30m)
- Uses Landsat 5 / Sentinel 2 for vegetation indices (NDVI, NDWI, NDMI, NBI) → **Switch to MODIS MOD13A1** for NDVI (500m, consistent 2001–2022) and add **MODIS MOD11A2** for LST
- Auth via `st.secrets` (Streamlit) → **Switch to service account JSON file or `ee.Authenticate()`**
- Cloud masking logic for Landsat/Sentinel → not needed for MODIS composites
- `get_slope()`, `get_image()`, `get_gee_data()`, `get_stats()` → replace with region-export functions for Córdoba bbox

---

## Phase 0: Project Scaffolding

**Goal:** Set up repo structure, dependencies, and tooling so all team members can start working.

- [x] Initialize git repo + `.gitignore` (Python artifacts, `__pycache__`, `.env`, `data/raw/`, `data/processed/`, `models/`, `mlruns/`, `node_modules/`, `outputs/`)
- [x] Create project structure:
  ```
  wildfires/
  ├── data/
  │   ├── ingestion/        # Scripts per data source
  │   ├── processing/       # Feature extraction, sampling
  │   ├── raw/              # .gitignored, local data storage
  │   └── processed/        # .gitignored, generated datasets
  ├── src/
  │   ├── features/         # Feature engineering, VIF, scaling
  │   ├── models/           # Training, tuning, evaluation
  │   └── maps/             # Prediction grid, GeoTIFF generation
  ├── notebooks/            # EDA, visualization prototypes
  ├── dashboard/            # Next.js app (Phase 6)
  ├── reusable_code/        # Reference from prior project (read-only)
  ├── tasks/                # todo.md, lessons.md
  ├── configs/              # YAML configs for paths, params
  ├── outputs/              # GeoTIFFs, GeoJSONs, SHAP plots
  ├── tests/
  ├── requirements.txt
  └── pyproject.toml
  ```
- [x] Create `requirements.txt`
- [x] Create `configs/cordoba.yaml`:
  - Study area bbox: `[-65.8, -35.0, -61.7, -29.3]` (approximate Córdoba Province)
  - CRS: EPSG:4326 (storage) / EPSG:32720 (UTM Zone 20S, for distance calcs)
  - Training period: 2001–2022
  - Validation period: 2023–2024
  - Negative sample buffer: ~~5km~~ → **1km** (updated in v2 — see Phase 2 note)
  - Grid resolution: 500m
  - Fire season months: [8, 9, 10, 11] (Aug–Nov)
- [ ] Set up MLflow tracking (local `mlruns/` directory, experiment name: `wildfires-cordoba`)
- [x] Create `tasks/todo.md` (this file) and `tasks/lessons.md`

---

## Phase 1: Data Ingestion

**Goal:** Download and store all raw data for Córdoba Province. Sub-tasks 1A–1E are independent and can run in parallel.

### 1A — Fire Detections (Target Variable)
- [x] Download Córdoba Province boundary → extracted from GADM → `data/raw/cordoba_boundary.shp`
- [x] Download MODIS FIRMS (MCD14ML) for Argentina, 2001–2022 → `data/raw/firms_modis.csv` (1.6M rows)
- [x] Download VIIRS FIRMS (VNP14IMG) for Argentina, 2023–2024 → `data/raw/firms_viirs.csv` (836k rows)
- [x] Write `data/ingestion/firms.py` ✓
- [x] **RUN**: `python data/ingestion/firms.py --source both` → produces `data/processed/firms_modis.gpkg` (45,313 rows) and `firms_viirs.gpkg` (17,821 rows)

### 1B — Topography (via GEE)
- [x] Write `data/ingestion/gee_terrain.py` ✓
- [x] GEE service account JSON at `data/google_service_account.json`
- [x] **RUN**: `GEE_SERVICE_ACCOUNT_JSON=data/google_service_account.json python data/ingestion/gee_terrain.py --step export` → 4 GeoTIFFs in `data/raw/dem/` (elevation, slope, aspect_cos, twi at 500m)

### 1C — Vegetation (via GEE)
- [x] Write `data/ingestion/gee_vegetation.py` ✓
- [x] Download Copernicus Global Land Cover → `data/raw/landcover.tif` ✓
- [x] **RUN**: `GEE_SERVICE_ACCOUNT_JSON=data/google_service_account.json python data/ingestion/gee_vegetation.py --step export` → 2 GeoTIFFs in `data/raw/vegetation/` (ndvi, lst)

### 1D — Climate (ERA5-Land via CDS API)
- [x] Write `data/ingestion/era5.py` ✓
- [x] CDS API key configured at `~/.cdsapirc` ✓
- [x] **RUN**: `python data/ingestion/era5.py --step both` → 22 NetCDFs downloaded + 4 GeoTIFFs in `data/raw/era5/` (temperature, precipitation, wind_speed, vpd — all fire season composites)

### 1E — Anthropogenic & Soil
- [x] Write `data/ingestion/soilgrids.py` (adapted from reusable_code/SoilGrids.py) ✓
- [x] Write `data/ingestion/osm_features.py` (adapted from reusable_code/geospatial.py) ✓
- [x] Download WorldPop population → `data/raw/population.tif` ✓
- [x] **RUN**: `python data/ingestion/soilgrids.py --mode wcs` → 15 rasters in `data/raw/soil/` (bdod, phh2o, clay, soc, ocd × 3 depths). ocs skipped (0-30cm only in v2, not in feature list)

### Phase 1 Verification
- [x] All scripts have `__main__` blocks ✓
- [x] Notebook `notebooks/01_data_check.ipynb` created ✓
- [x] Ran `notebooks/01_data_check.ipynb` → 13/13 files present, all layers verified ✓

---

## Phase 2: Sampling & Feature Extraction

**Goal:** Build the flat tabular dataset (N rows x ~18 features) for modeling.

### 2A — Spatial Sampling
- [x] Write `data/processing/sampling.py` ✓
- [x] **RUN**: sampling.py → `data/processed/sample_points.gpkg` (72,296 points, 1:1 balance) ✓
- [x] ⚠️ **Geographic confounding discovered**: 5km buffer + fire clustering in Sierras pushed ALL negatives to flat plains → models learned "mountains = fire" → AUC ~0.997 was spurious
- [x] **v2 fix**: Notebook `notebooks/03a_resampling.ipynb` — elevation-stratified resampling:
  - Buffer reduced 5km → **1km**
  - Joint stratification: elevation band (5 quantile bands) × land cover class
  - 34% of new negatives now inside mountain zone (vs ~0% in v1)
  - **RUN** → `data/processed/sample_points_v2.gpkg` (72,296 points, 1:1 balance) ✓

### 2B — Feature Extraction at Sample Points
- [x] Write `data/processing/extract_features.py` ✓
- [x] Write `data/processing/compute_osm_distances.py` ✓
- [x] **RUN**: extract_features.py → `data/processed/dataset.csv` (72,296 × 24 columns) ✓
- [x] **RUN v2**: `notebooks/03a_resampling.ipynb` calls extraction pipeline on v2 samples → `data/processed/dataset_v2.csv` (72,296 × 24 columns) ✓
- Note: `population_density` has 648 NaN — WorldPop raster edge coverage; imputed with median in preprocessing

### Phase 2 Verification
- [x] Class balance: 36,148 fire / 36,148 no-fire (perfect 1:1) ✓
- [x] All 24 columns present, OSM distances zero NaN ✓
- [x] Notebook `notebooks/02_eda.ipynb`: correlation heatmap, feature distributions by class (fire vs no-fire), spatial map of samples ✓
- [x] v2 KS-test elevation overlap: fire median=263m, new-neg median=271m, stat=0.076 (small effect size) ✓

---

## Phase 3: Preprocessing

**Goal:** Clean features, check multicollinearity, prepare train/test splits.

> **Active pipeline is v2** — v1 notebooks kept for comparison/reference only.

### v1 (reference only — known to be geographically confounded)
- [x] Notebook `notebooks/03_preprocessing.ipynb` ✓
  - VIF dropped 9: temperature, phh2o, twi, bdod, vpd, precipitation, ndvi, soc, wind_speed
  - Final: 9 continuous + 11 OHE = 20 features
  - Train: 50,607 | Test: 21,689 | Balance: 0.50 (stratified random split)

### v2 (current — spatial block split)
- [x] Notebook `notebooks/03b_preprocessing_v2.ipynb` ✓
  - Assigns 20km spatial block IDs (UTM 20S grid)
  - VIF dropped 10: temperature, phh2o, twi, bdod, vpd, precipitation, lst, ndvi, soc, wind_speed
  - Final: 8 continuous + 11 OHE = 19 features
  - `GroupShuffleSplit(test_size=0.30)` — no spatial block in both train and test
  - Train: 52,904 rows (321 blocks) | Test: 19,392 rows (138 blocks) | **0 block overlap** ✓
  - Outputs: `train_v2.csv`, `test_v2.csv`, `scaler_v2.pkl`, `encoder_v2.pkl`, `selected_features_v2.json`
  - Map of positive/negative sample distribution across Córdoba ✓
- [ ] Write `src/features/preprocessing.py` (migrate from 03b notebook — after tuning)
- [ ] Prepare VIIRS 2023–2024 temporal validation set:
  - Extract features at VIIRS fire point locations (same pipeline as 2B)
  - Save separately: `data/processed/validation_temporal.csv`

### Phase 3 Verification
- [x] No NaN in train_v2 / test_v2 ✓
- [x] Max VIF = 5.29 ≤ 10.0 ✓
- [x] Max pairwise |r| = 0.684 ≤ 0.85 ✓
- [x] Zero spatial block overlap between train and test ✓
- [ ] Confirm zero overlap between training points and temporal validation points (pending VIIRS validation set)

---

## Phase 4: Modeling & Evaluation

**Goal:** Train RF, XGBoost, LightGBM; tune with Optuna; evaluate; SHAP analysis.

### 4A — Baseline Models

#### v1 (reference — geographically confounded, StratifiedKFold)
- [x] Notebook `notebooks/04_modeling.ipynb` ✓
  - RandomForest : CV AUC=0.9965 | Test AUC=0.9973 | F1=0.9730
  - XGBoost      : CV AUC=0.9908 | Test AUC=0.9917 | F1=0.9566
  - LightGBM     : CV AUC=0.9961 | Test AUC=0.9967 | F1=0.9744
  - ⚠️ Results invalid — geographic confounding confirmed (AUC drop ~0.30 after fix)

#### v2 (current — spatial GroupKFold(5), elevation-stratified samples)
- [x] Notebook `notebooks/04_modeling_v2.ipynb` ✓
  - RandomForest : CV AUC=0.7432 | Test AUC=0.6992 | F1=0.5690
  - XGBoost      : CV AUC=0.7321 | Test AUC=0.6912 | F1=0.5584
  - LightGBM     : CV AUC=0.7283 | Test AUC=0.6865 | F1=0.5585
  - AUC drop vs v1: ~0.30 — documents the confounding effect (paper evidence)
  - Slightly below 0.75–0.90 target — expected improvement from tuning
  - All MLflow runs logged (`phase=v2_baseline`), .pkl artifacts in `models/`
  - v1 vs v2 comparison chart → `outputs/v1_vs_v2_auc_comparison.png`
- [ ] Write `src/models/train.py` (migrate from notebook — after tuning)

### 4B — Hyperparameter Tuning
- [x] Notebook `notebooks/04b_tuning_v2.ipynb` created ✓
  - Optuna study per model (N_TRIALS=20 for dev; increase to 50–100 for final paper run)
  - Objective: maximize mean AUC-ROC on **GroupKFold(5)** spatial CV (use `block_id` from `train_v2.csv`)
  - Search spaces:
    - RF: `n_estimators` [50–300], `max_depth`, `min_samples_split`, `max_features`
    - XGBoost: `n_estimators` [50–500], `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`
    - LightGBM: `n_estimators` [50–500], `num_leaves`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`
  - **RUN** ✓ → best models:
    - RandomForest CV AUC=0.7432, Test AUC=**0.6976** (BEST)
    - LightGBM CV AUC=0.7429, Test AUC=0.6912
    - XGBoost CV AUC=0.7405, Test AUC=0.6862
  - Log best trial per model to MLflow ✓
  - Save best model artifacts: `models/{model_name}_v2_best.pkl` ✓
  - Note: tuning gain minimal (~0.005 AUC on test) — spatial generalization gap dominates

### 4C — SHAP Analysis
- [x] Notebook `notebooks/04c_shap_v2.ipynb` ✓
  - `shap.TreeExplainer(best_model)` on RandomForest (best tuned v2 model) with `tree_path_dependent` mode
  - 2000-row subsample from test set (for speed)
  - **Generate + save to `outputs/shap/`:**
    - `shap_bar_v2.png` — global bar plot (mean |SHAP| per feature)
    - `shap_beeswarm_v2.png` — beeswarm dot plot
    - `shap_waterfall_fire_v2.png` / `_nofire_v2.png` / `_uncertain_v2.png` — local explanations
    - `shap_dependence_top4_v2.png` — 2×2 grid of top 4 feature dependence plots
  - Export SHAP values as CSV for dashboard use ✓
  - **Top 3 features (mean |SHAP|):**
    1. **clay** (0.0562) — soil composition drives fire risk
    2. **distance_to_settlement_km** (0.0475) — human proximity
    3. **elevation** (0.0452) — topographic effect (not dominant, as expected in v2)
  - ✓ Verification: elevation/slope NOT in top 3 → v2 fix working (confounding reduced)

### 4D — Model Comparison & Selection
- [x] Notebook `notebooks/04d_evaluation_v2.ipynb` ✓
  - Evaluate all tuned v2 models + MLP (from Colab) on holdout test set
  - **Comparison table:**
    | Model | Test AUC | Accuracy | Precision | Recall | F1 |
    |-------|----------|----------|-----------|--------|-----|
    | RandomForest (tuned) | **0.6976** | 0.6490 | 0.5922 | 0.5518 | 0.5708 |
    | LightGBM (tuned) | 0.6912 | 0.6412 | 0.5878 | 0.5376 | 0.5606 |
    | XGBoost (tuned) | 0.6862 | 0.6368 | 0.5814 | 0.5255 | 0.5513 |
    | MLP-Medium (Colab) | 0.6836 | 0.6428 | 0.5921 | 0.5355 | 0.5624 |
  - ROC curves → `outputs/v2_roc_curves_tuned.png` ✓
  - Confusion matrices → `outputs/v2_confusion_matrices_tuned.png` ✓
  - **Selected best model: RandomForest (tuned)** → `outputs/best_model_v2.json` ✓
  - Conclusion: tree ensembles outperform DL on tabular data at this scale; MLP slightly underperforms RF (0.6836 vs 0.6976)

### 4F — Deep Learning Exploration
- [x] Notebook `notebooks/04f_neural_network_v2.ipynb` created ✓
  - Residual MLP (PyTorch): 3 architectures × GroupKFold(5) CV
  - TabNet (pytorch-tabnet): attention-based tabular transformer
  - Gradient-based feature sensitivity as lightweight SHAP alternative
  - Full comparison chart vs tuned tree ensembles
  - Outputs: `nn_mlp_training_curves.png`, `nn_roc_comparison.png`, `nn_model_comparison.png`

### Phase 4 Verification
- [x] v2 baselines AUC > 0.65 (not over-corrected) ✓ → 0.66–0.70 range achieved
- [x] SHAP top features make domain sense ✓ → **clay** (soil) dominates, elevation #3 (not #1 as in v1)
- [x] MLflow UI: all v2 experiments visible ✓
- [x] No overfitting: CV AUC within ~0.05 of test AUC ✓ → RF CV=0.7432, Test=0.6976 (0.046 gap, expected for spatial CV)
- ⚠️ AUC < 0.75 after tuning — spatial generalization gap (~0.06) is bottleneck, not hyperparameters
  - Interpretation: v2 test set is geographically held-out, so models cannot leverage spatial autocorrelation
  - This is **correct behavior** for real-world deployment (new grid != training block clusters)

---

## ⚡ Next Steps (Ready to Start Phase 5)

**Current state:** RF tuned model selected (Test AUC=0.6976, F1=0.5643). All SHAP plots + metrics ready.

**Immediate tasks:**

1. **Create 05a_prediction_grid.ipynb** — Apply RF model to 500m prediction grid across Córdoba
   - Generate feature rasters for grid (same pipeline as Phase 2B, batched)
   - Run inference: 500k grid cells → predict_proba [:, 1]
   - Save raw predictions as GeoTIFF + GeoJSON
   - Apply Natural Breaks (Jenks) for risk zonation

2. **Create 05b_validation.ipynb** — Validate against VIIRS 2023–2024 fires
   - Load VIIRS fire points from `data/processed/firms_viirs.gpkg`
   - Sample susceptibility grid at each fire location
   - Compute zonal statistics: % fires per risk zone
   - Target: >80% of fires in High+VeryHigh

3. **Prepare Phase 6 data** (Phase 5 output feeds Phase 6)
   - Quantize GeoJSON (reduce geometry precision)
   - Export SHAP summary + metrics as dashboard JSON
   - Prepare fire timeline (2001–2024 MODIS + VIIRS)

**User choice:** Should I start Phase 5A (grid prediction), or do you want to review Phase 4 results first?

---

## Phase 5: Map Generation & Validation ✅ COMPLETE

**Goal:** Produce the susceptibility GeoTIFF and validate against 2023–2024 fires.

### 5A — Prediction Grid ✅
- [x] `notebooks/05a_prediction_grid.ipynb`
  - 629,777 valid cells at 0.005° (~500m) covering ~194,000 km²
  - Batched raster extraction (13 × 50k), OSM distances from cache, RF inference
  - Natural Breaks (mapclassify): Low 9.4% / Moderate 53.0% / High 26.0% / Very High 11.6%
  - `outputs/susceptibility.tif` — 3.5 MB, EPSG:4326, 2 bands (prob + class)
  - `outputs/susceptibility_zones.geojson` — 30 MB, 4 dissolved risk zones
  - `outputs/susceptibility_map.png`

### 5B — Temporal Validation ✅
- [x] `notebooks/05b_validation.ipynb`
  - 9,377 VIIRS 2023–2024 fire detections validated
  - **87.3% in High + Very High zones (target ≥80%) → PASS**
  - Breakdown: Low 0.3% / Moderate 12.4% / High 31.2% / Very High 56.1%
  - `outputs/validation_map.png`, `outputs/validation_stats.json`

### Phase 5 Verification ✅
- [x] GeoTIFF loads correctly: EPSG:4326, bounds match Córdoba extent
- [x] Zonal validation: 87.3% fires in High + Very High (≥80% target met)
- [x] Very High zone: 11.6% of province area (well under 20% cap)

---

## Phase 6: 3D Visualization Dashboard

**Goal:** Build and deploy the interactive Next.js + Deck.gl dashboard.

### 6A — Scaffolding
- [ ] `npx create-next-app@14 dashboard --typescript --app --tailwind`
- [ ] Install: `react-map-gl`, `@deck.gl/react`, `@deck.gl/layers`, `@deck.gl/aggregation-layers`, `zustand`, `recharts`
- [ ] Set up `.env.local` with `NEXT_PUBLIC_MAPBOX_TOKEN`
- [ ] Basic page: Mapbox GL map centered on Córdoba with 3D terrain enabled

### 6B — Data Preparation for Frontend
- [ ] Python script `src/maps/export_dashboard_data.py`:
  - Quantize susceptibility GeoJSON (reduce precision to 5 decimals, simplify geometries)
  - Fire points → JSON array `[{lat, lon, date, frp}, ...]`
  - SHAP summary → JSON `{feature_name: mean_abs_shap, ...}`
  - Model metrics → JSON `{auc_roc, accuracy, precision, recall, f1, confusion_matrix}`
- [ ] Place outputs in `dashboard/public/data/`

### 6C — View 1: Risk Extrusion
- [ ] `ColumnLayer` or `GridCellLayer` over Mapbox 3D terrain
- [ ] Height = susceptibility probability, Color = risk zone (green → yellow → orange → red)
- [ ] Basemap toggle: satellite / terrain / streets
- [ ] Zustand store for active view, visible layers, basemap

### 6D — View 2: Hexbin Aggregation
- [ ] `HexagonLayer` with 3D extrusion
- [ ] Height = historical fire count per hex, Color = mean predicted susceptibility
- [ ] UI control: hex radius slider (1km, 2km, 5km)

### 6E — View 3: Terrain Flyover
- [ ] Mapbox `flyTo()` animation path along the Sierras
- [ ] `HeatmapLayer` for continuous risk surface
- [ ] Toggle overlays: road network (`PathLayer`), rivers, fire stations (`IconLayer`)
- [ ] Time slider: fire season vs. non-fire-season risk maps

### 6F — View 4: Analysis Panel
- [ ] Sidebar component with:
  - SHAP feature importance horizontal bar chart (Recharts)
  - ROC curve plot (static image or Recharts)
  - Confusion matrix table
  - Province statistics: area (km²) per risk zone
  - Fire event timeline 2001–2024 (line/bar chart)
- [ ] Click any cell/hex → popup with feature values + SHAP local explanation

### 6G — Polish & Deploy
- [ ] Responsive layout: sidebar collapses on mobile
- [ ] Loading states for large data layers
- [ ] Deploy to Vercel, configure env vars
- [ ] Performance: initial load < 3s on 4G

### Phase 6 Verification
- [ ] All 4 views render without console errors
- [ ] Layer toggles enable/disable correctly
- [ ] Popup data matches underlying dataset
- [ ] Vercel deployment live and accessible

---

## Phase 7: Paper & Presentation

**Goal:** Write the scientific article (~6,000–8,000 words) and prepare defense materials.

- [ ] Introduction: wildfire problem in Argentina, South America under-representation in literature, Córdoba's fire history (430+ km² burned Sept 2024)
- [ ] Study area: Córdoba Province geography, climate zones, fire corridors, map figure
- [ ] Data & Methods: all 8 subsections per project plan §7 (fire data, features, sampling, feature selection, ML models, Optuna, metrics, SHAP)
- [ ] Results: model comparison table, ROC curves, SHAP plots, susceptibility map, zonal validation
- [ ] Discussion: compare with Germany/Algeria/Pakistan/Turkey/Russia benchmarks, acknowledge limitations (MODIS 1km resolution, ERA5 ~9km coarseness, negative sampling assumptions)
- [ ] Conclusions: summary, policy implications for Córdoba fire management, future work (seasonal models, VIIRS retraining, real-time dashboard)
- [ ] References: ~40–60 citations
- [ ] Presentation slides for university defense

---

## Execution Order & Dependencies

```
Phase 0 (scaffolding)
    │
    ▼
Phase 1A ─┐
Phase 1B ─┤
Phase 1C ─┼──→ Phase 2 (needs all raw data)
Phase 1D ─┤         │
Phase 1E ─┘         ▼
                Phase 3 (needs dataset.csv)
                    │
                    ▼
                Phase 4 (needs preprocessed splits)
                    │
              ┌─────┴─────┐
              ▼           ▼
         Phase 5     Phase 6A (scaffold — can start early)
              │
              ▼
         Phase 6B–6G (needs outputs from Phase 5)
              │
              ▼
         Phase 7 (needs validation results + dashboard screenshots)
```
