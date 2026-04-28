# Gap Analysis: Our Project vs. NASA DEVELOP Córdoba (Summer 2024)

Reference: `nasa_project.md` — NASA DEVELOP National Program, partner INTA, Summer 2024.
Our project: `CLAUDE.md` + `tasks/todo.md` (current state, April 2026).

The goal of this document is to enumerate where the NASA team made methodological or data-source choices that we did not, so we can decide which to adopt. It is **not** a claim that their results are better in general — the two projects have different framings — but several of their choices are worth borrowing.

---

## 0. Headline Metrics Comparison (for context, not apples-to-apples)

| Metric | NASA (logistic regression on Sept 2020 event) | Ours (RF v2, continuous 2001–2022, spatial-block CV) |
|---|---|---|
| Accuracy | 70.2% | — |
| Precision | 72.0% | — |
| Recall | 83.1% | — |
| F1 | 77.1% | 0.571 |
| Specificity | 50.4% | — |
| AUC-ROC | (not reported) | 0.698 |
| Zonal validation | — | 87.3% of independent VIIRS 2023–2024 fires in High + Very High zones |

**Why not directly comparable:** NASA classifies burned vs. unburned sites *within a single event window* (Sept 2020), which is an easier task than 22-year province-wide susceptibility. Our spatial-block CV AUC of 0.70 is, if anything, the honest version of the ~0.997 AUC we got in v1 before fixing geographic confounding.

---

## 1. Framing Differences (decisions, not gaps)

These are scope choices. We should not "close" them — we should be aware of them when reading their results.

| Dimension | NASA | Us |
|---|---|---|
| Target horizon | Specific event (Sept 2020) with 6-month lead-up (Mar–Aug 2020) | Continuous susceptibility, 2001–2022 |
| Baseline | 2010–2019 monthly climatology for anomaly computation | No baseline; raw seasonal aggregates |
| Validation | In-sample logistic/RF on same period | Temporal hold-out (VIIRS 2023–2024) + spatial GroupKFold |
| Target construction | MODIS MCD64A1 + FireCCI5 burned area | MODIS FIRMS MCD14ML hotspots (point detections, dedup to 500m grid) |
| Sampling of negatives | Unburned sites excluding anything burned Aug 2018–Aug 2020 | Stratified (elevation × land cover), 1km buffer, 1:1 ratio |

---

## 2. True Gaps — Missing Variables

| Variable | NASA source | Our status | Recommendation |
|---|---|---|---|
| **Evapotranspiration (ET)** | Terra MODIS MOD16A2 V6.1, 500m, 8-day | ❌ not ingested | **Add.** Low effort via GEE (`MODIS/061/MOD16A2`). NASA found ET non-significant in logistic regression but 4th in RF importance — modest lift, cheap to include. |
| **Dynamic soil moisture** | SMAP SPL4SMGP.007, 9km, 3-hour | ❌ substituted with *static* SoilGrids (clay, soc, bdod, etc.) | **Add.** SMAP is a known strong fire precursor. Static soil properties are a different signal (texture/composition, not current wetness). Ingest via NASA Earthdata or GEE (`NASA/SMAP/SPL4SMGP/007`). Constraint: SMAP starts 2015, so full 2001–2022 coverage is impossible — use it as a secondary feature set from 2015 onward, or switch to a longer-record surrogate (ERA5-Land `volumetric_soil_water_layer_1`). |
| **Wildland–Urban Interface (WUI)** | U. Wisconsin–Madison WUI 2020, 10m | ~ approximated by `distance_to_settlement_km` | **Nice-to-have.** Our proxy already ranks #2 in SHAP importance, so the signal is captured. An explicit WUI classification (intermix/interface/non-WUI) would sharpen human-ignition modeling but is not a blocker. |

---

## 3. True Gaps — Methodology

### 3.1 No anomaly features

NASA's central insight is that *departures* from the 2010–2019 monthly climatology (negative precipitation anomaly, positive LST anomaly, negative NDVI anomaly) preceded the Sept 2020 event. We model raw seasonal aggregates only.

- **Impact:** Extreme-dry years look the same as average years in our features unless the raw value crosses an absolute threshold. Anomalies normalize for seasonality and pixel-level climate regime.
- **Adoption:** Compute per-pixel monthly z-scores (or simple differences) vs. a 2001–2019 baseline for NDVI, LST, precipitation, VPD. Extract lead-up windows (1/3/6-month cumulative precipitation deficit, preceding-season LST anomaly) at each sample point. Lands in `src/features/` — new module, e.g. `anomalies.py`.

### 3.2 VIF filter dropped NASA's top predictors

Our v2 VIF>10 filter removed **NDVI, precipitation, LST, VPD, soc, wind_speed, bdod, phh2o, temperature, TWI** (per Explore report from `notebooks/03b_preprocessing_v2.ipynb`). NASA's RF ranked these as #1 NDVI, #2 precipitation, #6 LST — all *retained*.

- **Impact:** We are very likely throwing away signal. A VIF of 10–20 is typical in the ecology literature; 10 is the strict econometrics cutoff for inference, not prediction. For tree models, multicollinearity hurts interpretability but not predictive accuracy.
- **Adoption:** Either (a) relax VIF to 15–20, (b) switch to correlation-only filter (|r|>0.85), or (c) keep features correlated with land-cover dummies since trees split on whichever is most informative. Document physically-meaningful features we re-admit. Re-run v3 modeling.

### 3.3 No logistic regression baseline

NASA ran logistic regression primarily for inference — sign and significance of each driver. We only have SHAP on tree models.

- **Impact:** We cannot make claims of the form "higher elevation significantly increases fire probability (p<0.05, β=X)" in the paper.
- **Adoption:** Add a logistic regression fit in `notebooks/04*_modeling_v2.ipynb` (or sibling). Report coefficients, standard errors, p-values. Use statsmodels, not sklearn, so we get the statistical summary. Treat it as interpretability, not as the prediction model.

### 3.4 No Partial Dependence Plots

NASA reports publishable, citable thresholds:
- *"NDVI 0.25–0.30 peaks fire probability, then drops as vegetation density/health increases."*
- *"Precipitation 10–15 mm is the high-risk zone; probability drops non-linearly above that."*

We have SHAP dependence plots, which are close but not the fire-susceptibility-literature convention.

- **Adoption:** Add PDPs (`sklearn.inspection.partial_dependence`) for the top 5–7 features of the best RF. Include in the paper alongside SHAP. Low effort.

### 3.5 Fire-season aggregation loses temporal dynamics

We aggregate climate/NDVI across Aug–Nov into per-year scalars. NASA kept monthly resolution across Mar–Aug and showed that the *lead-up trajectory* (drying trend through winter) is predictive.

- **Adoption (compatible with our continuous framing):** Add per-sample lag features — e.g. cumulative precipitation deficit over the 30/90/180 days *before* each fire detection, LST anomaly in the preceding month, NDVI trend (slope of last 3 MOD13A1 composites). This keeps one row per sample but encodes the trajectory NASA exploited.

### 3.6 No event-window validation (Sept 2020)

The Sept 2020 fires are arguably the most important event in our study period, and we have not used them as a dedicated holdout.

- **Adoption:** Train on 2001–2019 only, score on Sept 2020 detections. Report: (a) fraction of Sept 2020 burned area in our High+Very High zones, (b) AUC against a matched negative sample drawn from 2019. This is a supplementary validation section in the paper, effectively free given the pipeline already exists — just a different time filter.

---

## 4. Where We Are Stronger (keep doing)

- **Spatial-block cross-validation.** Our v1 → v2 fix showed AUC crashing from 0.997 → 0.70 when we stopped leaking geography across folds. NASA's write-up does not describe precautions against spatial autocorrelation, so their 70% accuracy may not fully rule it out.
- **Longer training window.** 22 years of MODIS FIRMS vs. a single event.
- **Independent temporal hold-out.** VIIRS 2023–2024 is a genuinely unseen period and sensor.
- **Deeper interpretability.** Full SHAP suite (bar, beeswarm, waterfall, dependence) vs. NASA's variable-importance ranking + PDPs.
- **Tree ensembles + tuning.** RF / XGBoost / LightGBM with Optuna; NASA reports logistic + RF only.

---

## 5. Prioritized Action Items

Ordered by (expected predictive lift) ÷ (effort).

| # | Priority | Action | Where it lands | Effort |
|---|---|---|---|---|
| 1 | **P0** | Relax/replace VIF filter and re-run modeling with NDVI, precipitation, LST retained | `notebooks/03b_preprocessing_v2.ipynb` → v3 | Low |
| 2 | **P0** | Add monthly anomaly features vs. 2001–2019 baseline (NDVI, LST, precipitation, VPD) + 30/90/180-day lag windows | new `src/features/anomalies.py`; re-extract at sample points | Medium |
| 3 | **P0** | Sept 2020 event-window validation | `notebooks/05*` — new validation section | Low |
| 4 | **P1** | Add logistic regression baseline (statsmodels, coefficients + p-values) | `notebooks/04*_modeling_v2.ipynb` | Low |
| 5 | **P1** | Add Partial Dependence Plots for top features | same notebook | Low |
| 6 | **P1** | Add MOD16A2 Evapotranspiration | `data/ingestion/gee.py` (extend) | Low |
| 7 | **P2** | Add dynamic soil moisture (ERA5-Land layer 1 for full period, or SMAP from 2015) | `data/ingestion/era5.py` or new `smap.py` | Medium |
| 8 | **P2** | Swap `distance_to_settlement_km` proxy for explicit WUI layer | `data/ingestion/` + `src/features/` | Medium–High |

P0 items (#1–#3) are the highest-leverage: #1 likely raises AUC the most per hour of work because we know we dropped informative features; #2 addresses the drought-precursor story NASA built their paper on; #3 is nearly free and gives us a paper-grade event validation.

---

## 6. Caveats

- NASA's 70.2% accuracy is on a balanced burned-vs-unburned classification within a single month and region — a much narrower task than 22-year continuous susceptibility. Our AUC of 0.70 on the harder task is not obviously worse.
- Some NASA results (e.g. ET not significant in logistic, 4th in RF) suggest their RF importance is partly driven by collinearity with the significant variables. We should not assume every variable they used will help us.
- SMAP's 9 km resolution and post-2015 coverage are real constraints; ERA5-Land volumetric soil water may be the more practical substitute for the full 2001–2022 window.
