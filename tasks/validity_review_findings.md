# Validity Review Findings

Status legend: **FAIL** = must fix before publication | **WARN** = must discuss in limitations | **PASS** = verified correct

---

## Critical FAILs (fix before any further runs)

### FAIL-1 — Model/Feature-Set Mismatch
**Plan item:** 0.3, 5.3

**Finding:** All three saved best models (`randomforest_v2_best.pkl`, `xgboost_v2_best.pkl`, `lightgbm_v2_best.pkl`) were trained with **27 features**. The file `selected_features_v2.json` was updated on Apr 28 (models saved Apr 27) to add `et` and `soil_moisture` — 29 features total. The models were **never retrained**. The current pipeline is internally broken: any re-run of `05a_prediction_grid.ipynb` or evaluation with the current JSON will raise a ValueError.

**Evidence:**
```
randomforest_v2_best:  n_features_in_=27
xgboost_v2_best:       n_features_in_=27
lightgbm_v2_best:      n_features_in_=27
selected_features_v2.json → 29 features
susceptibility.tif: generated Apr 27 20:16 (before JSON update Apr 28 22:36) → valid for 27 features
```

**Consequence:** The susceptibility map does not use `et` or `soil_moisture` despite them being present in `train_v2.csv`. These are physically important (evapotranspiration = fuel moisture proxy; soil moisture = antecedent moisture).

**Remediation:**
1. Re-run `04b_tuning_v2.ipynb` with the full 29-feature set (N_TRIALS ≥ 50 — see FAIL-5).
2. Re-run `05a_prediction_grid.ipynb` and `05b_validation.ipynb`.
3. Update `best_model_v2.json` and all output artefacts.

---

### FAIL-2 — VIIRS Validation Data Leaks Into Negative Sampling
**Plan item:** 2.2.b, 7.1

**Finding:** `data/processing/sampling.py` loads `firms_viirs.gpkg` (VIIRS 2023–2024 detections) and includes them in the fire-exclusion tree used to reject negatives within 5 km. This means every training negative is forced to be >5 km away from locations that **actually burned in 2023–2024** — the validation set. The model then "validates" by checking if those same locations receive high probabilities. This circular logic inflates the 89.4% zonal-validation figure.

**Evidence (sampling.py lines 73–79):**
```python
def load_all_fire_points_utm():
    """Including VIIRS ensures negatives are also far from 2023-2024 fires."""
    for fname in ("firms_modis.gpkg", "firms_viirs.gpkg"):
```

**Remediation:**
1. Remove `firms_viirs.gpkg` from the exclusion tree in `sampling.py`. Use only `firms_modis.gpkg` (2001–2022) for training negatives.
2. Re-generate `sample_points_v2.gpkg`, `dataset_v2.csv`, `train_v2.csv`, `test_v2.csv`.
3. Retrain all models and re-run prediction grid.
4. Re-quote the 89.4% metric (expected to drop; report both numbers in the paper with explanation).

---

### FAIL-3 — Correlation Filter Applied to Full Data Before Train/Test Split
**Plan item:** 4.2

**Finding:** In `03b_preprocessing_v2.ipynb`, the correlation filter (`correlation_filter()`) is executed at **Cell 12**, before the `GroupShuffleSplit` at **Cell 16**. Feature selection uses target-correlation computed on the full dataset (train + test), leaking test labels into feature selection.

**Cell order verified:**
```
Cell 12: correlation_filter
Cell 16: GroupShuffleSplit (split)
Cell 17: StandardScaler fit
```

**Dropped features (vpd, bdod)** were selected using correlation with `label` computed over both train and test rows. In a strict sense, this violates the test-set holdout — the dropped set could differ if computed on train-only.

**Remediation:**
1. Move the correlation filter to run after the split, fitting it only on `df_train`.
2. Apply the resulting feature set to `df_test` (do not re-compute on test).
3. Re-run preprocessing, retraining, and map generation.

---

### FAIL-4 — Class Balance Severely Imbalanced Between Train and Test
**Plan item:** 4.5

**Finding:** `GroupShuffleSplit` is not stratified, resulting in a 9.7 percentage-point class-balance gap:
```
Train: 52,904 rows  fire_rate = 0.5262
Test:  19,392 rows  fire_rate = 0.4285
Delta = 0.0977  (threshold: 0.05)
```
The model is evaluated on a test set where fires are significantly rarer than in training. Threshold-dependent metrics (precision, recall, F1, accuracy) are biased; confusion-matrix plots are misleading.

**Remediation:**
Replace `GroupShuffleSplit` with `StratifiedGroupKFold` (available in sklearn ≥ 0.24) for the holdout split. Re-run preprocessing → training → evaluation.

---

### FAIL-5 — Optuna Tuning Used N_TRIALS = 20 (Not 50–100)
**Plan item:** 5.2

**Finding:** The tuning notebook header states "Set N_TRIALS = 100 for the final paper run." The actual variable assignment is `N_TRIALS = 20`. The saved best models come from a 20-trial search, which is insufficient for 5–9 hyperparameters. The MLflow tag `n_trials = 20` confirms this.

**Remediation:**
Re-run `04b_tuning_v2.ipynb` with `N_TRIALS = 100`. Overwrite `*_v2_best.pkl` files. Quote final AUC from this run in the paper.

---

## WARNings (must be addressed in the paper's Limitations / Methods sections)

### WARN-1 — Calibration: Slight Overconfidence in Mid-Range
**Plan item:** 5.4

**Measured (LightGBM best, 27-feature holdout test):**
```
pred=0.548  actual=0.489  delta=0.059
pred=0.649  actual=0.583  delta=0.066  ← worst bin
pred=0.748  actual=0.685  delta=0.064
ECE = 0.0306  (threshold 0.05 → OK)
Brier score = 0.2017
```
The model overestimates probability in the 0.55–0.75 range. ECE is below the hard threshold (0.0306 < 0.05), so this is a WARN not a FAIL. However, the susceptibility map probabilities in that range are visually higher than the actual fire rate. The risk-zone boundaries (especially the Moderate/High break at ~0.40) may be better calibrated after fixing FAIL-1 and FAIL-2.

**Remediation:** After retraining, fit `CalibratedClassifierCV(method='isotonic', cv=StratifiedGroupKFold(5))` on the training set. Plot a reliability diagram in the paper.

---

### WARN-2 — Feature Importance and Permutation Importance Strongly Disagree
**Plan item:** 5.7

**Measured on LightGBM best (27-feature):**

| Feature | FI rank | PI rank | Gap |
|---|---|---|---|
| precipitation | 1 | 8 | **−7** |
| clay | 11 | 1 | **+10** |
| ndvi | 9 | 3 | **+6** |
| lc_40 (cropland) | 18 | 9 | **+9** |
| wind_speed | 3 | 2 | — |
| elevation | 4 | 4 | — |

`clay` is ranked 11th by the tree's built-in importance but is the **single most important feature** by permutation AUC-drop (0.032 drop). This is a consequence of correlated features — the tree split-count measure conflates shared credit between correlated predictors (clay, soc, phh2o). SHAP plots based on `feature_importances_` will convey the wrong message.

**Remediation:**
- Report permutation importance in the paper (not built-in FI).
- Run SHAP `TreeExplainer` on the holdout test set and use `shap_values` instead of `feature_importances_`.
- Add a sentence in the SHAP section: "NDVI, LST, and temperature are correlated; their individual SHAP attributions are not uniquely decomposable."

---

### WARN-3 — Sensitivity of the 80% Validation Metric to Classification Scheme
**Plan item:** 6.4

**Measured (9,377 VIIRS 2023–2024 fire points against the susceptibility map):**

| Scheme | High + VH |
|---|---|
| Jenks / Natural Breaks (current) | **89.4%** |
| Quantile breaks (25/50/75) | 92.9% |
| Equal interval | 80.0% |
| Fixed p > 0.5 / p > 0.7 | 80.0% |
| Null model (random proba, Jenks breaks) | 59.8% |

The 89.4% figure is scheme-dependent. The model beats the null by ~30 percentage points, which is meaningful — but the absolute headline number would drop to 80.0% under equal-interval or fixed-threshold schemes. The paper must report the null-model baseline alongside the main result.

Note: these figures are still inflated by the VIIRS leakage (FAIL-2). After fixing FAIL-2, all numbers will shift.

**Remediation:**
- Add a sensitivity table to the paper.
- Add a null-model paragraph in the validation section.
- After retraining, re-run with all four schemes.

---

### WARN-4 — ERA5 and SoilGrids Resolution Mismatch
**Plan item:** 3.1

**Measured unique values per feature across 72,296 samples:**

| Feature | Unique values | Resolution |
|---|---|---|
| phh2o | **75** | SoilGrids 250m |
| clay | 1,015 | SoilGrids 250m |
| soc | 1,416 | SoilGrids 250m |
| temperature | 1,692 | ERA5 ~9 km |
| precipitation | 1,713 | ERA5 ~9 km |
| wind_speed | 1,714 | ERA5 ~9 km |
| soil_moisture | 1,710 | ERA5 ~9 km |
| elevation | 2,265 | SRTM 30m → 500m |

ERA5 cells (~9 km) are shared across many 500 m sample points → the model cannot learn within-ERA5-cell variation. `phh2o` has only 75 unique values across 72k rows (essentially categorical for the model). These limitations are inherent to the data sources but must be disclosed.

**Remediation:** Add a paragraph in Methods/Data: "ERA5 climate variables have an effective resolution of ~9 km; within-ERA5-cell climate variation is not captured. SoilGrids pH has a coarser effective resolution (~7 km) due to its mapping algorithm. These resolutions are coarser than the 500 m prediction grid."

---

### WARN-5 — NaN → 0 Before StandardScaler on the Prediction Grid
**Plan item:** 3.3, 6.2

**Finding:** In `05a_prediction_grid.ipynb` (Cell 9), continuous features with NaN are filled with `np.nan_to_num(..., nan=0.0)` **before** applying the fitted StandardScaler. For a feature with mean μ and std σ, raw 0 becomes `(0 − μ) / σ` after scaling — a non-zero anomaly proportional to the mean. This is not the same as mean-imputation (which would produce a z-score of 0 after scaling).

For the current run, the only column needing imputation was `population_density` (handled correctly with median before this block). If other features have NaN in edge-boundary cells, they are incorrectly zero-imputed.

**Remediation:**
Replace the `np.nan_to_num` block with:
```python
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='median')
imputer.fit(X_train[CONT_FEATURES])   # fit on training data
cont_array = imputer.transform(cont_array)   # use on grid
```
Or, if NaN is rare and only from boundary clipping, document the cell count and explain the negligible impact.

---

### WARN-6 — OHE Unknown Land Cover Class Assignment
**Plan item:** 4.6

**Finding:** In `05a_prediction_grid.ipynb`, NaN land-cover cells are filled with `encoder.categories_[0][0]` (the smallest LC class by integer code) before OHE encoding. This forces unknown LC cells to be encoded as if they belong to a specific LC class — producing a 1 in one OHE column rather than all zeros. The `handle_unknown='ignore'` behaviour would produce all zeros, which is more defensible.

**Remediation:**
Remove the `np.where(np.isnan(...), encoder.categories_[0][0], lc_values)` line. The OHE encoder's `handle_unknown='ignore'` already handles NaN correctly if passed as a valid input.

---

### WARN-7 — StandardScaler Applied to Tree Models Obscures SHAP Interpretability
**Plan item:** 4.3

**Finding:** `StandardScaler` is applied to all continuous features. Tree ensembles are scale-invariant, so this does not affect AUC/F1. However, SHAP plots (`04c_shap_v2.ipynb`) show contributions in **standardized units** (z-scores) rather than physical units (°C, mm, km), making the plots difficult to interpret without back-transformation. A wind speed SHAP attribution of "+0.5 standardised units" is meaningless to a reader.

**Remediation:**
Either (a) drop scaling for tree models and remove it from the preprocessing pipeline, or (b) back-transform SHAP x-axis values to physical units using `scaler.inverse_transform`. Option (a) also simplifies the prediction grid.

---

### WARN-8 — VIF Informational Only: SHAP Attributions for Correlated Features Unreliable
**Plan item:** 4.1

**Finding:** VIF is computed but not applied ("tree ensembles handle multicollinearity"). This is correct for prediction accuracy. However, for SHAP-based interpretation, correlated features share credit inconsistently. The SHAP value of NDVI (correlated with LST, r > 0.85 threshold candidate) may differ substantially depending on which correlated feature is visited first in a tree path.

**Remediation:** Add a sentence in the SHAP section: "Because NDVI and LST, and temperature and precipitation, are moderately correlated, their individual SHAP attributions should be interpreted collectively rather than in isolation."

---

### WARN-9 — N_TRIALS = 20 in the Paper's Best Models (re-stated from FAIL-5)
Already captured as FAIL-5. The paper **must not** claim "50–100 Optuna trials" in the Methods section if the actual run used 20.

---

## PASSed Checks

| Item | Result |
|---|---|
| **3.5** Temporal leakage: month/fire_season_flag in MODEL_FEATURES | **PASS** — confirmed absent from all_model_features |
| **2.2** Negative month=9 not in model | **PASS** — temporal features excluded |
| **5.4** Calibration ECE < 0.05 | **PASS** — ECE=0.0306 |
| **7.2** Null-model baseline | **PASS** — model beats random by ~30pp (89.4% vs 59.8%) |
| **7.4** Bootstrap CI reported | **PASS** — AUC=0.7430 [0.7358, 0.7498] |
| **5.3** Best-model selection transparent | **PASS** — LightGBM best by holdout AUC=0.7428, logged in best_model_v2.json |
| **6.3** OSM cached vectors used consistently | **PASS** — same cache for train and grid |
| **1.6** UTM Zone 20S covers Córdoba bbox | **PASS** — [-65.8°, -61.7°] well within Zone 20S [-66°, -60°] |
| **0.1** Scaler/encoder saved and reloaded correctly | **PASS** — verified against test predictions |

---

## Prioritised Remediation Roadmap

### Must fix (re-run entire pipeline):
1. **FAIL-2** Remove VIIRS from negative exclusion → re-sample → re-extract → re-split → retrain
2. **FAIL-3** Correlation filter on train-only → rebuild preprocessing
3. **FAIL-4** StratifiedGroupKFold for holdout split
4. **FAIL-5** N_TRIALS = 100 for tuning
5. **FAIL-1** is resolved automatically after steps 1–4 (et and soil_moisture will be properly included)

### Fix prediction grid only (no retraining needed):
6. **WARN-5** NaN imputation before scaling
7. **WARN-6** OHE unknown handling

### Paper writing (no code change):
8. **WARN-1** Add reliability diagram; discuss calibration
9. **WARN-2** Use permutation importance in the paper; discuss SHAP limitations
10. **WARN-3** Add classification-scheme sensitivity table; add null baseline
11. **WARN-4** Disclose ERA5/SoilGrids resolution in Methods
12. **WARN-7** Back-transform SHAP axes to physical units
13. **WARN-8** Add SHAP correlation caveat

---

## Key Numbers (Current Pipeline — Pre-Fix)

| Metric | Value |
|---|---|
| Best model | LightGBM (27 features, 20 trials) |
| Test AUC | 0.7428 [95% CI: 0.7358–0.7498] |
| Test F1 | 0.616 |
| CV AUC | 0.779 ± (GroupKFold-5) |
| ECE (calibration) | 0.0306 |
| Brier score | 0.2017 |
| Zonal validation: High+VH | 89.4% (Jenks) |
| Null model baseline | 59.8% |
| Class balance delta (train/test) | 9.7 pp (FAIL) |
| N_TRIALS used | 20 (FAIL — should be ≥ 50) |

*After fixing FAILs 1–5, re-quote all numbers in a `validity_review_findings_v2.md`.*
