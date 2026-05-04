# Validity Review Plan — Wildfire Susceptibility, Córdoba

Audit plan for the Phase 1–5 pipeline (data → sampling → features → preprocessing → models → susceptibility map → validation). Each section lists (a) the **decision under review**, (b) the **specific question(s) to answer**, (c) the **evidence/check** to run, and (d) the **pass criterion** that determines whether the decision needs revision.

The goal is to surface methodological risks that a peer reviewer at a remote-sensing or fire-ecology journal (e.g. *IJWF*, *RSE*, *NHESS*) would raise — **before** the article is written.

> Output of the review: a single `tasks/validity_review_findings.md` document with one row per item below — **PASS / WARN / FAIL** + short justification + remediation pointer. Items marked FAIL must be fixed before publication; WARN items must be discussed in the limitations section of the paper.

---

## 0. Cross-Cutting Concerns (do these first)

- **0.1 Reproducibility**
  - Re-run `data/processing/sampling.py` and `extract_features.py` with `--random-seed` from config; diff `dataset_v2.csv` SHA-256 against the committed copy.
  - Re-run `04_modeling_v2.ipynb` end-to-end and confirm AUCs reproduce within ±0.005.
  - **Pass:** byte-identical positive samples; AUC reproducible.

- **0.2 Data lineage**
  - For each feature column in `dataset_v2.csv`, confirm raster path, CRS, units, and date range are documented (extend `notebooks/data_dictionary_wildfire.html` if missing).
  - **Pass:** every column has source + units + temporal coverage recorded.

- **0.3 Code/notebook drift**
  - `dataset.csv` vs `dataset_v2.csv` and `03_preprocessing.ipynb` vs `03b_preprocessing_v2.ipynb` coexist. Confirm v1 artefacts are no longer referenced anywhere in `05*`, `dashboard/`, or `src/maps/`.
  - **Pass:** v1 is dead code or explicitly archived.

---

## 1. Data Ingestion (Phase 1)

### 1.1 FIRMS fire detections — the target variable
- **Decisions:**
  - MODIS MCD14ML 2001–2022 used for *training*; VIIRS VNP14IMG 2023–2024 used for *validation*.
  - Confidence filter: MODIS `nominal+`, VIIRS `n+` (config `cordoba.yaml:41–42`).
  - All months retained (no filter to fire season at the raw stage).
- **Questions:**
  - Are MODIS "nominal" detections accepted by the literature for susceptibility mapping, or should we restrict to "high" only? What is the false-positive rate over Córdoba (industrial gas flares, brick kilns, agricultural burns)?
  - MODIS pixel ≈1 km, VIIRS ≈375 m. Mixing them as "the same target" for training-vs-validation introduces a sensor change — does the paper acknowledge this?
  - Is there a known **prescribed-burn / agricultural-burn** mask for Argentina that should be removed (these are not "wildfires" in the susceptibility sense)?
- **Checks:**
  - Plot detection density per month for MODIS vs VIIRS over 2023 (overlap year) and report ratio.
  - Quantify how many MODIS detections fall on cropland (Copernicus class 40) — these are likely stubble-burning events, not wildfire.
  - Cross-reference against any official Manejo del Fuego (SNMF) statistics for Córdoba 2010–2022.
- **Pass criterion:** Either (a) document and accept the inclusion of agricultural fires as part of "fire occurrence", or (b) re-run sampling after filtering them out and re-quote AUC.

### 1.2 Static climate composite (ERA5 fire-season mean)
- **Decision:** ERA5 variables collapsed to a *single* fire-season (Aug–Nov) mean across 2001–2022 → one raster per variable.
- **Question:** A model using a 22-year mean cannot learn *interannual* drivers (drought year vs wet year). Is this consistent with the paper's claim of "wildfire susceptibility"? Susceptibility (static landscape risk) vs danger/hazard (dynamic, weather-driven) need to be cleanly separated in the framing.
- **Check:** Confirm in the article that the mapped quantity is **long-term susceptibility**, not seasonal danger. If the paper claims to predict *where fires occur in 2023–2024*, the static-climate choice is a methodological mismatch.
- **Pass criterion:** Article framing is internally consistent with the climate aggregation level.

### 1.3 Topography
- **Decision:** SRTM 30 m → resampled/exported at 500 m (`gee.dem_scale_m: 30` but config also references `ndvi_scale_m: 500`). Slope, aspect-cos, TWI derived in GEE.
- **Questions:** Resampling method (mean? bilinear?) on slope is non-trivial — averaging slopes underestimates extremes. Is the resampling defensible?
  - TWI at 500 m is essentially noise — TWI requires fine-scale flow accumulation. Confirm whether to keep it.
- **Check:** Inspect the GEE export script (`gee_terrain.py`) for the reducer used on slope. Compare TWI variance at 500 m to the within-cell range at 30 m on a 10×10 km test patch.
- **Pass criterion:** Reducer is documented; TWI either justified or dropped.

### 1.4 Vegetation (NDVI / LST / ET)
- **Decisions:** MODIS MOD13A1 NDVI, MOD11A2 LST, MOD16A2GF ET — all collapsed to fire-season mean over 2001–2022.
- **Question:** Same as 1.2 — using a long-term mean NDVI hides drought-driven curing of fuels, which is the biggest predictor of fire risk in semi-arid systems.
- **Check:** Compute NDVI anomaly (Aug–Nov mean of *that year* minus 2001–2022 climatology) for the fire-positive years; assess whether anomaly is a stronger predictor than mean.
- **Pass criterion:** Either justify the mean (susceptibility framing) or add anomaly as a feature.

### 1.5 Population, soil, OSM, land cover
- **Decision:** WorldPop 2020 used for all years; SoilGrids depths averaged 0–30 cm; OSM downloaded *now* and applied to fires from 2001.
- **Question:** OSM road / settlement networks have grown substantially in 25 years. A 2024 OSM road may not have existed in 2001 → distance-to-road is anachronistic for early fires.
- **Check:** Quantify expected magnitude using GHSL built-up evolution layer for Córdoba. If >10–20 % of the 2024 road network is post-2001, this is material.
- **Pass criterion:** Either restrict the training period to ≥2010 (when OSM coverage stabilises in Argentina) or add a sensitivity analysis.

### 1.6 CRS handling
- **Decision:** Storage EPSG:4326, distance computations in EPSG:32720 (UTM 20S).
- **Question:** Córdoba spans roughly -65.8° to -61.7° lon — the eastern third is in **UTM zone 20**, the western two-thirds are in **UTM zone 20** as well? UTM 20S covers -66° to -60°, so this is fine — confirm and document.
- **Pass criterion:** Confirmed; no zone-edge distortion.

---

## 2. Spatial Sampling (Phase 2A — `data/processing/sampling.py`)

### 2.1 Positive sample deduplication
- **Decision:** Snap MODIS detections to a 500 m UTM grid; keep one centroid per occupied cell. 1.6 M raw → 45 k positives.
- **Questions:**
  - Deduplication discards repeat fires in the same cell across 22 years — but **frequency** of burning is itself a strong signal. Is the loss of repeat-fire information acceptable?
  - The "first" date is kept per cell — used downstream for `month`. If the cell burned in different months in different years, the kept month is arbitrary.
- **Checks:**
  - Histogram of repeat-fire counts per 500 m cell. If many cells burned ≥5 times, consider a *frequency-weighted* target or a count-regression formulation.
  - Verify whether `month` is actually used as a model feature (it appears in `dataset_v2.csv` but is excluded from `MODEL_FEATURES` in `selected_features_v2.json`).
- **Pass criterion:** If `month` is *not* in the model, deduplication is fine for binary occurrence; document the loss of frequency information.

### 2.2 Negative sampling — the most consequential decision
- **Decisions:**
  - Random points inside Córdoba boundary.
  - **Excluded if within 5 km of any MODIS or VIIRS fire detection**, all years.
  - **Stratified by Copernicus land cover** in proportion to province-wide LC distribution.
  - 1:1 ratio with positives (n_neg = n_pos).
- **Critical questions:**
  - **(a) Buffer = 5 km is asymmetric.** MODIS pixel is 1 km; a "no-fire" point 1.5 km from a real fire is excluded but a fire 4.9 km away is allowed. The 5 km value comes from `cordoba.yaml:25` (originally documented as 1 km in the project plan, then changed). Justify against literature (Jaafari et al., 2019; Ghorbanzadeh et al., 2019 typically use 1–2 km).
  - **(b) Including VIIRS 2023–2024 in the exclusion buffer leaks validation data into training.** Negatives in the training set are explicitly chosen to be far from places that *will* burn in 2023–2024. This deflates the AUC penalty the model should pay. **This is the single most important issue to fix.**
  - **(c) Stratifying *negatives* by land cover but letting *positives* take whatever LC they have biases the model.** Fires are not LC-uniform — they concentrate in shrub/grass/cropland. If negatives are forced to the province-wide LC distribution, the model learns "LC = forest → negative" trivially, even though forest does burn.
  - **(d) 1:1 ratio is artificial.** True positive prevalence in 500 m cells × 22 years is far <50 %. Calibration of predicted probabilities is meaningless without a prevalence correction (Phillips & Elith, 2013).
  - **(e) Province-only domain ignores the rest of Argentina.** Models can spuriously latch onto the province boundary (edges of Córdoba).
- **Checks:**
  - **Re-run sampling** with: VIIRS *removed* from the exclusion tree (use only MODIS 2001–2022). Re-train and compare AUC.
  - **Re-run sampling** with negatives drawn from the *positives' LC distribution* (not the province distribution). Re-train and compare.
  - **Re-run with 1:5 and 1:10 imbalance** (or weight-corrected loss). Check whether ranking metrics (AUC, AP) and Brier score change materially.
  - Plot positives vs negatives in (lat, lon) space — is there a systematic spatial gap (sierras vs llanura)?
- **Pass criterion:**
  - VIIRS exclusion **must** be removed from training-time negatives → re-quote all metrics.
  - Class-ratio sensitivity must be reported (a table of AUC at 1:1, 1:5, 1:10).
  - LC-stratification rationale documented or replaced with positive-matched stratification.

### 2.3 Negative sampling within province boundary
- **Decision:** Random uniform in bbox, accept if inside polygon.
- **Question:** Does this cause edge artefacts (cells within 500 m of the border have biased neighborhood statistics for OSM distances etc.)? Probably minor; verify.
- **Check:** Map the sample density — uniform inside, sharp drop at border.

### 2.4 Random seed and rejection-sampling stability
- **Decision:** Single seed (42), single oversampling factor (4×).
- **Check:** Re-run with seeds {1, 7, 100} and confirm AUC variance < 0.01.

---

## 3. Feature Extraction (Phase 2B — `extract_features.py`)

### 3.1 Point-sampling rasters of mismatched resolution
- **Decision:** All rasters sampled with `rasterio.sample()` at the exact (lon, lat) — nearest neighbour.
- **Question:** ERA5 cells are ~9 km. A 500 m positive and a 500 m negative within the same ERA5 cell get the *identical* climate value. The model can't learn within-cell variation, and clustered positives all share the same value (artificially low feature variance for the positive class).
- **Check:** Compute the unique-value count for each climate feature per class. If `temperature` has only ~50 unique values across 90 k samples, that's a red flag.
- **Pass criterion:** Document the resolution-mismatch limitation; consider downscaling ERA5 (lapse-rate correction with DEM) or using TerraClimate.

### 3.2 Soil-depth aggregation
- **Decision:** Mean of 0–5, 5–15, 15–30 cm.
- **Question:** Simple mean ignores that the layers have different thicknesses. Weighted mean (5/30, 10/30, 15/30) is the correct depth-weighted average.
- **Check:** Recompute soil features as depth-weighted means; quantify difference.
- **Pass criterion:** Either depth-weight or document the choice.

### 3.3 NaN handling at extraction time
- **Decision:** Sentinel `<= -9000` → NaN; nodata → NaN (except for ndvi/slope/aspect_cos where 0 is valid).
- **Question:** `extract_features.py` correctly preserves NaN; **but `notebooks/05a_prediction_grid.ipynb` converts NaN → 0 *before* StandardScaler**. After scaling this becomes a non-zero anomaly proportional to the feature mean, biasing the prediction grid in NaN regions.
- **Check:** Count cells in the prediction grid with any NaN feature; map them. If non-trivial, this is a FAIL.
- **Pass criterion:** Replace `np.nan_to_num(..., nan=0.0)` with median-imputation matching the training-time treatment.

### 3.4 OSM distance computation
- **Decision:** Densify lines every 500 m, build cKDTree, query nearest point. Cap of 500 m sampling.
- **Question:** For a road that's >500 m away the densification step is fine; for points <500 m from a road, the discretisation introduces an error of up to 250 m (~half the spacing).
- **Check:** For 1 % of samples compute the *exact* distance via shapely `.distance()` and quantify the error distribution.
- **Pass criterion:** Mean error < 50 m and max < 250 m; otherwise reduce spacing.

### 3.5 Temporal features
- **Decision:** `month` and `fire_season_flag` columns are written but not in `MODEL_FEATURES` (per `selected_features_v2.json`).
- **Question:** Confirm they're truly excluded from training and prediction. If they were included, the negative-sample assignment of `month=9` would be a label leak (model learns "month=9 → negative bias" because all negatives were tagged 9).
- **Check:** Grep for `month` and `fire_season_flag` in modelling notebooks; confirm absence in feature matrices.
- **Pass criterion:** Both excluded; otherwise FAIL.

---

## 4. Preprocessing (Phase 3 — `03b_preprocessing_v2.ipynb`)

### 4.1 VIF "informational only"
- **Decision:** Compute VIF, but drop nothing — justified as "tree ensembles handle multicollinearity".
- **Question:** True for *prediction*, but multicollinearity *does* affect SHAP value attribution and feature-importance interpretation, both of which the paper relies on. Acknowledge in the SHAP discussion.
- **Pass criterion:** Discussion section calls out that SHAP attributions among correlated features (NDVI/LST, temp/VPD) are not unique.

### 4.2 Pairwise correlation filter (|r| > 0.85)
- **Decision:** Drop the feature with weaker target-correlation in each pair.
- **Question:** This is a reasonable heuristic but couples feature selection to the target — borderline data-leakage if computed on full data (train + test). Verify it's done before the train/test split *or* on training data only.
- **Check:** Read the notebook flow — currently the correlation filter is applied to `df` (full data) before the split. Re-run with filter on train-only and confirm the same features are dropped.
- **Pass criterion:** Either re-do on train-only, or document that the filter set is robust.

### 4.3 StandardScaler on tree models
- **Decision:** Scale all continuous features; fit on train, apply to test.
- **Question:** Tree ensembles are scale-invariant — scaling is unnecessary. Worse, it makes SHAP plots show "standardised units" instead of physical units (°C, km), hurting interpretability.
- **Check:** Are SHAP plots labelled with raw or scaled units? If scaled, viewers can't tell what NDVI=2.3 means.
- **Pass criterion:** Either drop scaling for tree models, or back-transform SHAP plots to physical units.

### 4.4 Spatial block size = 20 km
- **Decisions:** UTM grid 20 km × 20 km; ~ blocks; `GroupShuffleSplit(test_size=0.30)`.
- **Question:** Block size should approximate the **spatial autocorrelation range** of model errors. For wildfire features (NDVI, climate, soil), the range is often 30–100 km. 20 km may be too small → optimistic AUC.
- **Checks:**
  - Compute a Moran's I or empirical variogram on RF residuals from the v2 holdout. If autocorrelation persists at lag > 20 km, block size is too small.
  - Sensitivity: re-run preprocessing + modelling at block_size = 10, 20, 40, 80 km. Plot AUC vs block size. Reported AUC should be at the size where autocorrelation drops to noise.
- **Pass criterion:** Block-size sensitivity table reported; chosen size justified empirically.

### 4.5 GroupShuffleSplit is not stratified
- **Decision:** `GroupShuffleSplit` does not preserve class balance.
- **Check:** Print fire-rate per fold and per train/test. If it varies > 5 percentage points, use `StratifiedGroupKFold` (sklearn ≥0.24).
- **Pass criterion:** Class balance preserved (≤5 pp drift) or switch splitter.

### 4.6 One-hot encoding land cover
- **Decision:** OHE with `handle_unknown='ignore'`. Prediction grid has a fallback for unseen LC classes (sets to most frequent training class).
- **Question:** "Most frequent training class" is a silent bias for cells with rare LC classes. Better: leave as all-zero OHE (current `handle_unknown='ignore'` behaviour) and *not* override with a fake class.
- **Check:** Read `05a_prediction_grid.ipynb` LC handling; confirm whether the override creates spurious predictions.
- **Pass criterion:** No fake class assignment.

---

## 5. Modeling & Tuning (Phase 4 — `04_modeling_v2.ipynb`, `04b_tuning_v2.ipynb`)

### 5.1 Cross-validation: GroupKFold
- **Decision:** `GroupKFold(n_splits=5)` on `block_id`.
- **Questions:**
  - Not stratified — class balance can drift. Use `StratifiedGroupKFold`.
  - 5 folds is the *minimum* defensible; 10 is more conventional.
- **Pass criterion:** Switch to `StratifiedGroupKFold(5)` (or explain). Re-quote CV AUC ± std.

### 5.2 Optuna tuning budget
- **Decision:** `N_TRIALS = 20` (notebook comment: "increase to 50–100 for final paper run"). Best models saved as `*_v2_best.pkl`.
- **Check:** Confirm whether the saved best models came from a 20-trial or 100-trial run. If 20, this is insufficient for paper claims.
- **Pass criterion:** ≥50 trials per model for the run that produced `*_v2_best.pkl`; record n_trials in MLflow.

### 5.3 Choice of best model
- **Decision:** RF `randomforest_v2_best.pkl` is used by `05a_prediction_grid.ipynb`.
- **Question:** Was RF actually best, or chosen for convenience? Compare CV AUC of RF, XGB, LGBM, MLP and pick by holdout AUC.
- **Check:** `outputs/v2_final_comparison_table.png`, `outputs/best_model_v2.json`. If LGBM or XGB has higher CV AUC, defend the RF choice (calibration? interpretability? speed?).
- **Pass criterion:** Best-model selection criterion is explicit and consistent with the chosen model.

### 5.4 Probability calibration
- **Decision:** No calibration step is in any notebook.
- **Question:** RF probabilities are typically over-confident; they feed directly into Natural Breaks, which then drives the validation metric. A miscalibrated probability distorts the risk-zone boundaries.
- **Check:** Plot reliability diagram (sklearn `calibration_curve`) on holdout test. If ECE > 0.05, fit `CalibratedClassifierCV(method='isotonic', cv=GroupKFold)` and re-export the susceptibility map.
- **Pass criterion:** Reliability diagram in the paper; calibration applied if needed.

### 5.5 Class weights / sampling
- **Decision:** None. 1:1 sampled positives/negatives, default class weights.
- **Question:** With the prevalence-corrected ratio (see 2.2), class weights become necessary. Tie this to the imbalance sensitivity test.
- **Pass criterion:** Documented.

### 5.6 Decision threshold for confusion matrices
- **Decision:** Default 0.5 used in `outputs/v2_confusion_matrices*.png`.
- **Question:** With 1:1 sampling, 0.5 is fine; with corrected imbalance, 0.5 is wrong. Use Youden's J or the threshold maximising F1 on a CV fold.
- **Pass criterion:** Threshold selection justified, not implicit.

### 5.7 Feature importance & SHAP
- **Decisions:** Standard `*.feature_importances_` plus SHAP on the best model (`04c_shap_v2.ipynb`).
- **Questions:**
  - SHAP on RF with correlated features attributes inconsistently — pair with permutation importance for cross-check.
  - Is SHAP computed on training, test, or a sampled subset? Use the holdout test for unbiased attributions.
  - If features were standardised, are SHAP plots back-transformed to physical units (see 4.3)?
- **Pass criterion:** Permutation-importance and SHAP agree on top 5 features; physical-unit axes.

---

## 6. Susceptibility Map (Phase 5A — `05a_prediction_grid.ipynb`)

### 6.1 Grid resolution
- **Decision:** `GRID_RES = 0.005°` ≈ "500 m at 32°S".
- **Question:** Cells are not square at this latitude — Δlat ≈ 555 m, Δlon ≈ 470 m. Negligible for visualisation, but the documented "500 m grid" is approximate. Use a metric grid (UTM 500 m) or document.
- **Pass criterion:** Documented or switched to UTM grid.

### 6.2 NaN handling on the prediction grid (already raised in 3.3)
- **Decision:** `np.nan_to_num(..., nan=0.0)` *before* scaling.
- **Pass criterion:** Replace with the same imputation used at training (median for population_density; document treatment for other features that produced NaN).

### 6.3 OSM features at prediction time
- **Decision:** Same OSM cache used; same densification spacing.
- **Question:** OK for spatial consistency; same anachronism caveat as 1.5.

### 6.4 Risk-zone classification — Natural Breaks (Jenks)
- **Decisions:** `mapclassify.NaturalBreaks(proba, k=4)` → Low / Moderate / High / Very High; sanity check "Very High < 20 % of province".
- **Critical questions:**
  - Jenks is computed on the *predicted-probability distribution*, which depends on the model. Different models produce different breaks → the same cell can be "High" under RF and "Moderate" under XGB. Is this a property the paper wants?
  - "80 % of validation fires in High + Very High" depends on (a) the breaks, (b) how aggressive the model is in producing high probabilities. A model that always predicts 0.99 will trivially put all fires in Very High. The metric is **not** independent of model overconfidence — calibration matters here.
  - Is there a literature standard (e.g. quantile breaks, expert thresholds at p > 0.5/0.7)?
- **Checks:**
  - Re-classify with quantile breaks (25/50/75/95) and equal-interval breaks; report sensitivity of the "80 %" metric to each scheme.
  - Compute % fires in High+VH for a *null model* (uniform random probability). The headline metric must clearly exceed the null.
- **Pass criterion:** Sensitivity to classification scheme reported; null-model baseline reported.

### 6.5 Province boundary effects
- **Decision:** Predict only inside Córdoba.
- **Question:** Province border cuts arbitrarily through landscapes — the susceptibility map shows discontinuities at administrative boundaries that are physically meaningless. For paper figures, predict in a buffer (~10 km) and crop, to avoid ugly edges.

---

## 7. Temporal Validation (Phase 5B — `05b_validation.ipynb`)

### 7.1 Independence of validation set
- **Decisions:**
  - Validate on VIIRS 2023–2024 (independent in time and partly in sensor).
  - Target: ≥80 % of VIIRS fires in High + Very High.
- **Critical questions:**
  - **VIIRS was used to define the negative-sample buffer (see 2.2.b).** This means the model was trained to push down probabilities everywhere VIIRS detected fires in 2023–2024 → it is *almost guaranteed* to assign high probability to those locations once they're back in the dataset. Truly independent validation requires re-training without VIIRS in the exclusion buffer.
  - VIIRS ≠ MODIS — sensor differences in detection threshold and pixel size mean a "validation fire" at high VIIRS probability may not have crossed the MODIS threshold. Quantify the bias.
  - Many 2023–2024 fires occur in cells that *also burned* in 2001–2022 (training data). This is not temporal independence — it is **temporal autocorrelation**. Subset validation to cells with **no MODIS fire 2001–2022** ("first-time burns") and re-quote the 80 % metric.
- **Pass criterion:** Re-train without VIIRS leakage; report 80 % metric on (a) all VIIRS fires and (b) first-time-burn VIIRS fires only. Both numbers go in the paper.

### 7.2 Baseline comparison
- **Decision:** No null/baseline model.
- **Question:** What is the 80 % metric for: (a) random map, (b) MODIS fire-frequency density (smoothed kernel density of training fires), (c) elevation-only model?
- **Pass criterion:** Baselines reported; the model must beat fire-frequency density meaningfully (~10+ percentage points), otherwise "the map is just a smoothed history of past fires".

### 7.3 Spatial validation (in addition to temporal)
- **Decision:** Spatial CV used during training; no held-out *region* test.
- **Question:** Hold out one geographic stratum (e.g. Sierras Chicas) entirely from training and validate on it. This tests transferability across landscape units.
- **Pass criterion:** Region-holdout AUC reported; if it collapses (<0.7), document as a limitation.

### 7.4 Statistical significance
- **Decision:** Point estimates only.
- **Question:** Bootstrap 95 % CIs for AUC and the 80 % metric (resample VIIRS fires). Report mean ± CI.
- **Pass criterion:** Confidence intervals reported.

---

## 8. Dashboard / Visualisation (Phase 6, `dashboard/`)

Out of scope for *scientific* validity, but check:
- **8.1** GeoJSON / GeoTIFF served to the dashboard is the **same** artefact validated in §7. Compare SHA-256 of the served file vs `outputs/susceptibility.tif`.
- **8.2** Dashboard's risk-zone colour scheme matches paper figures.
- **8.3** No client-side post-processing of probabilities (e.g. opacity tied to probability) that would mislead the user.

---

## 9. Documentation & Reporting (for the article)

- **9.1** Write a one-page *methodological flow diagram* (Phase 1 → Phase 5) that the reviewer can read in 30 s. Include arrows for data flow and dotted lines for validation checks.
- **9.2** Limitations section must explicitly cover: agricultural-burn inclusion (1.1), static-climate framing (1.2), OSM anachronism (1.5), VIIRS leakage if not fixed (2.2.b), 1:1 imbalance (2.2.d), ERA5 resolution mismatch (3.1), Jenks dependency (6.4).
- **9.3** All AUCs in the paper must be **CV mean ± std** plus **holdout** plus **bootstrap 95 % CI** — never a single point estimate.

---

## 10. Execution Order for the Review

Recommended sequence (each step ~½–1 day):

1. **Day 1 — Quick wins**: 0.1, 0.2, 1.6, 3.5, 4.5 (binary checks, no rerun).
2. **Day 2 — Read-only audits**: 1.1, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.6, 5.1, 5.3, 6.1, 6.5.
3. **Day 3 — Diagnostic analyses (no retraining)**: 3.1 (unique-value count), 3.4 (OSM error), 4.4 (variogram), 5.4 (calibration), 5.7 (permutation importance), 6.4 (classification sensitivity), 7.2 (baselines), 7.4 (bootstrap CIs).
4. **Day 4–5 — Re-runs (the expensive ones)**: 2.2 (re-sample without VIIRS, with corrected stratification, with class imbalance) → 4.5 → 5.1 → 5.2 (≥50 trials) → 6.x → 7.1 → 7.3.
5. **Day 6 — Compile `validity_review_findings.md`** with PASS/WARN/FAIL per item and a prioritised remediation list for the article.

---

## 11. Deliverables

- `tasks/validity_review_findings.md` — one row per item above.
- `outputs/review/` — all diagnostic plots (variogram, reliability diagram, sensitivity tables, baseline ROCs, classification-scheme sensitivity).
- A short `outputs/review/summary.md` listing the top 5 items that **must** be fixed before submission.

---

## Top 5 *a-priori* concerns (gut-call before running anything)

1. **VIIRS leakage in negative sampling** (§2.2.b) — likely the largest single source of inflated metrics.
2. **Static climate / NDVI vs susceptibility framing** (§1.2, 1.4) — easy to mis-claim what the map represents.
3. **NaN → 0 before scaling on the prediction grid** (§3.3 / 6.2) — silent bug that biases the map in low-data regions.
4. **Jenks-dependent 80 % validation metric** (§6.4) — the headline number is sensitive to a post-hoc choice.
5. **Class-ratio of 1:1 with no calibration** (§2.2.d, 5.4) — predicted probabilities are not interpretable as risk.
