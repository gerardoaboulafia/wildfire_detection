# Wildfire Susceptibility Mapping — Córdoba, Argentina

## Project Plan

---

## 1. Executive Summary

Build a machine learning-based wildfire susceptibility map for Córdoba Province, Argentina, with an interactive 3D visualization dashboard. The project addresses a documented gap in the literature — South America is severely underrepresented in ML-based wildfire research despite containing 21% of global forest area. Córdoba is one of Argentina's most fire-affected provinces (430+ km² burned in September 2024 alone), yet has no published ML susceptibility model.

**Output:** A scientific article suitable for university journal submission + a deployed interactive 3D dashboard.

**Core methodology:** Binary classification (fire occurred / didn't occur) using satellite-derived fire detections and ~15 environmental features, trained with ensemble ML models, interpreted with SHAP, and visualized as a 3D susceptibility surface over real terrain.

---

## 2. Why This Project Works

### 2.1 Problems with the current Forest-Fire project

| Problem | Root Cause | How this project fixes it |
|---|---|---|
| Target variable created by KMeans on a derived ratio — not defensible in peer review | Manual discretization with no domain justification | Binary target (fire/no-fire) from satellite detections — no discretization needed |
| Model always predicts class B (~90% probability) | Imbalanced classes from arbitrary clustering | Balanced sampling strategy with equal fire/non-fire points |
| 5-minute inference time from live API calls | 3 overlapping weather APIs queried in real-time | Static/seasonal features only — inference is instant |
| Class D recall = 10%, class B recall = 37% | Categories don't reflect real fire behavior differences | Binary classification avoids multi-class confusion entirely |
| 120 meteorological features with high multicollinearity | 3 weather services measuring similar things across 4 time windows | ~15 curated features from single sources, VIF-checked |
| California focus — hundreds of competing papers | Saturated research domain | Córdoba, Argentina — virtually no published ML susceptibility work |

### 2.2 Publication angle

The paper's core contribution is straightforward and defensible: **"First ML-based wildfire susceptibility map for Córdoba Province, Argentina, combining satellite fire detections, ERA5 climate data, and multi-source geospatial features, validated against 2023-2024 fire events."**

This follows the exact template of recently published papers (2024-2025) in Scientific Reports, Natural Hazards, Fire Ecology, and Applied Sciences — same methodology applied to Germany, Algeria, Turkey, Pakistan, and India. Applying it to an under-studied region with real policy relevance is a recognized contribution.

---

## 3. Data Sources

### 3.1 Target Variable — Fire Detections

| Source | Product | Resolution | Coverage | Access |
|---|---|---|---|---|
| NASA FIRMS | MODIS Active Fire (MCD14ML) | 1 km | 2001–present | https://firms.modaps.eosdis.nasa.gov/download/ |
| NASA FIRMS | VIIRS Active Fire (VNP14IMG) | 375 m | 2012–present | Same portal |
| GWIS GlobFire | Individual fire events (from MCD64A1) | 500 m | 2001–2023 | https://gwis.jrc.ec.europa.eu |
| datos.gob.ar | Official Argentine fire statistics | Provincial/departmental | Multi-year | https://datos.gob.ar/dataset/ambiente-incendios-forestales |

**Strategy:** Use MODIS FIRMS for 2001–2022 as training data. Reserve VIIRS 2023–2024 for independent validation. Argentine government data for cross-validation and contextualization.

**Negative samples:** Generate random non-fire points within Córdoba Province, constrained to be >5 km from any fire detection and stratified by land cover type to avoid sampling bias.

### 3.2 Feature Variables

| Category | Variable | Source | Resolution | Notes |
|---|---|---|---|---|
| **Topography** | Elevation | SRTM DEM | 30 m | Via Google Earth Engine |
| | Slope | Derived from DEM | 30 m | Degrees |
| | Aspect | Derived from DEM | 30 m | Cosine-transformed |
| | Topographic Wetness Index (TWI) | Derived from DEM | 30 m | Soil moisture proxy |
| **Vegetation** | NDVI (seasonal composites) | MODIS MOD13A1 | 500 m | Via GEE — fire season avg |
| | Land Surface Temperature | MODIS MOD11A2 | 1 km | Via GEE — fire season avg |
| | Land Cover | Copernicus Global Land Cover | 100 m | Categorical |
| **Climate** | Temperature (annual/seasonal mean) | ERA5-Land | ~9 km | Via Climate Data Store |
| | Precipitation (annual/seasonal sum) | ERA5-Land | ~9 km | Single consistent source |
| | Wind speed (seasonal mean) | ERA5-Land | ~9 km | Replaces 3-API approach |
| | VPD / relative humidity | ERA5-Land | ~9 km | Dryness indicator |
| **Anthropogenic** | Distance to roads | OpenStreetMap via OSMnx | Vector | **Reuse existing pipeline** |
| | Distance to rivers | OSM / HydroSHEDS | Vector | Fire barrier proxy |
| | Population density | WorldPop | 100 m | Ignition source proxy |
| **Soil** | Soil organic carbon, clay, pH, bulk density | SoilGrids | 250 m | **Reuse existing pipeline** |

**Total: ~15-18 features** — manageable, interpretable, and consistent with published methodology.

### 3.3 What you salvage from the Forest-Fire project

| Component | Reuse Level | Notes |
|---|---|---|
| SoilGrids pipeline (`data/SoilGrids.py`) | Direct reuse | Same API, just change coordinates to Córdoba |
| OSM spatial features (`data/geospatial.py`) | Heavy reuse | Road/river distances, land use — same logic |
| GEE integration (`data/GEE.py`) | Adapt | Switch from weather queries to NDVI/LST extraction |
| Feature engineering classes (`src/feature_engine.py`) | Adapt | Keep scaling, encoding; drop KMeans discretization |
| MLflow infrastructure (`mlflow/`) | Direct reuse | Same experiment tracking setup |
| LightGBM / XGBoost modeling | Direct reuse | Same algorithms, cleaner features |
| Streamlit app pattern (`app.py`) | Replace | New Next.js + Deck.gl frontend |

---

## 4. Methodology

### 4.1 Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: DATA INGESTION                                        │
│                                                                  │
│  NASA FIRMS ──→ Fire points (lat, lon, date, confidence, FRP)   │
│  GEE ─────────→ NDVI, LST, DEM, slope, aspect                  │
│  ERA5-Land ───→ Temperature, precipitation, wind, VPD           │
│  SoilGrids ──→ SOC, clay, pH, bulk density                     │
│  OSM/OSMnx ──→ Road network, river network, settlements        │
│  WorldPop ───→ Population density grid                          │
│  Copernicus ─→ Land cover classification                        │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: FEATURE EXTRACTION                                    │
│                                                                  │
│  For each sample point (fire or non-fire):                      │
│    • Extract raster values at point location                    │
│    • Compute distances (roads, rivers, settlements)             │
│    • Compute terrain derivatives (slope, aspect, TWI)           │
│    • Assign land cover class                                    │
│    • Add temporal features (month, fire season flag)            │
│                                                                  │
│  Output: Flat tabular dataset (N rows × ~18 features)           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: PREPROCESSING                                         │
│                                                                  │
│  • VIF check — drop features with VIF > 10                      │
│  • Correlation matrix — remove redundant pairs (r > 0.85)       │
│  • StandardScaler on continuous features                        │
│  • One-hot encode categoricals (land cover)                     │
│  • 70/30 stratified train/test split                            │
│  • Reserve 2023–2024 VIIRS data as independent validation set   │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: MODELING                                              │
│                                                                  │
│  Train 4 models with 10-fold stratified CV:                     │
│    1. Random Forest (baseline)                                  │
│    2. XGBoost                                                   │
│    3. LightGBM                                                  │
│    4. Neural Network (MLP — optional stretch goal)              │
│                                                                  │
│  Hyperparameter tuning: Optuna (50–100 trials per model)        │
│  Track all experiments in MLflow                                │
│                                                                  │
│  Metrics: AUC-ROC, accuracy, precision, recall, F1              │
│  Feature importance: SHAP (global + local explanations)         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: MAP GENERATION                                        │
│                                                                  │
│  • Create prediction grid (~500m cells across Córdoba)          │
│  • Extract features for every grid cell                         │
│  • Run best model → probability per cell                        │
│  • Classify into 4 risk zones (Natural Breaks / Jenks):        │
│      Low | Moderate | High | Very High                          │
│  • Validate: overlay 2023–2024 fires on susceptibility map     │
│  • Report % of actual fires falling in High/Very High zones     │
│                                                                  │
│  Output: GeoTIFF raster + GeoJSON polygons for visualization    │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6: 3D VISUALIZATION DASHBOARD                            │
│                                                                  │
│  Next.js + react-map-gl + Deck.gl                               │
│  See Section 5 for full details                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Model Evaluation Strategy

**Primary metric:** AUC-ROC (standard in susceptibility mapping literature).

**Validation layers:**

1. **Cross-validation** — 10-fold stratified CV on 2001–2022 data
2. **Holdout test set** — 30% random split from training period
3. **Temporal validation** — 2023–2024 VIIRS fire detections overlaid on susceptibility map
4. **Zonal validation** — percentage of actual fires falling in High + Very High zones (target: >80%, consistent with published benchmarks)

---

## 5. 3D Visualization Dashboard

### 5.1 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Framework | Next.js 14 (App Router) | You already know it from BA transit; SSR for performance |
| Map engine | Mapbox GL JS via react-map-gl | Beautiful terrain, satellite imagery, 3D terrain built-in |
| 3D data layers | Deck.gl | Industry standard for geospatial data viz; HexagonLayer, ColumnLayer, HeatmapLayer, TerrainLayer |
| State management | Zustand | Lightweight, clean — better than Redux for dashboards |
| Charts | Recharts or Plotly.js | For sidebar statistics |
| Deployment | Vercel | Free tier, perfect for Next.js |

### 5.2 Dashboard Views

**View 1: Risk Extrusion over Real Terrain**
- Mapbox GL terrain layer (3D topography of the Sierras de Córdoba)
- Deck.gl `ColumnLayer` or `GridCellLayer` extruding fire probability as vertical columns
- Height = susceptibility score (0–1), Color = risk category (green → yellow → orange → red)
- User can orbit, zoom, tilt — see how risk follows mountain ridges and valleys
- Toggle satellite vs. terrain basemap

**View 2: Hexbin Aggregation (like your BA transit project)**
- Deck.gl `HexagonLayer` with 3D extrusion
- Height = historical fire density (number of fires per hex)
- Color = model-predicted susceptibility
- This shows where the model agrees/disagrees with historical patterns
- Adjustable hex radius (1km, 2km, 5km)

**View 3: Interactive Terrain Flyover**
- Mapbox GL "fly to" animation along the Sierras
- Risk heatmap draped over terrain (`BitmapLayer` with terrain mesh)
- Show fire stations, road network, rivers as overlay toggle
- Time slider: switch between seasonal risk maps (summer vs. winter)

**View 4: Analysis Panel**
- SHAP feature importance bar chart
- Confusion matrix / ROC curve (static)
- Provincial statistics: total area per risk category
- Fire event timeline (2001–2024)
- Click any hex/cell → popup with all feature values + prediction breakdown

### 5.3 Key Deck.gl Layers

```
┌──────────────────────────────────────────────────────────────┐
│                     LAYER STACK                               │
│                                                               │
│  ┌─ Deck.gl Overlay ──────────────────────────────────────┐  │
│  │                                                         │  │
│  │  ColumnLayer (risk extrusion)                          │  │
│  │    ↕ toggle                                            │  │
│  │  HexagonLayer (aggregated fire density)                │  │
│  │    ↕ toggle                                            │  │
│  │  HeatmapLayer (continuous risk surface)                │  │
│  │    ↕ toggle                                            │  │
│  │  ScatterplotLayer (historical fire points)             │  │
│  │    ↕ toggle                                            │  │
│  │  PathLayer (road network)                              │  │
│  │    ↕ toggle                                            │  │
│  │  IconLayer (fire stations)                             │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ Mapbox GL Base ───────────────────────────────────────┐  │
│  │                                                         │  │
│  │  3D Terrain (Mapbox terrain-rgb tileset)                │  │
│  │  Satellite / Streets / Outdoors basemap (toggle)        │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Team Allocation (4+ members, 3–6 months)

### Suggested Role Split

| Role | Person | Responsibilities |
|---|---|---|
| **Data Engineer** | Member 1 | Fire data ingestion (FIRMS), ERA5 download, GEE scripts for NDVI/LST/DEM, data pipeline orchestration |
| **Geospatial Analyst** | Member 2 | OSM feature extraction (reuse existing code), SoilGrids pipeline (reuse), distance computations, spatial sampling strategy, GeoTIFF generation |
| **ML Engineer** | Member 3 | Model training, Optuna tuning, MLflow tracking, SHAP analysis, VIF/correlation checks, evaluation metrics |
| **Frontend Developer** | Member 4 | Next.js + Deck.gl dashboard, all 4 views, layer controls, deployment to Vercel |
| **Paper Lead** | Shared / 5th member | Literature review, methodology writing, figures, results interpretation |

### Timeline

```
Month 1 ──────────────────────────────────────────────────────
  Week 1-2:  Literature review + data audit
             - Download MODIS FIRMS for Córdoba (2001–2024)
             - Set up GEE scripts for NDVI, LST, DEM
             - Download ERA5-Land for Córdoba region
             - Set up project repo + MLflow

  Week 3-4:  Feature extraction pipeline
             - Adapt SoilGrids pipeline to Córdoba coords
             - Adapt OSM pipeline to Córdoba region
             - Build spatial sampling (fire + non-fire points)
             - Extract raster values at all sample points

Month 2 ──────────────────────────────────────────────────────
  Week 5-6:  EDA + Preprocessing
             - VIF analysis, correlation matrix
             - Feature distributions, class balance check
             - Data cleaning, outlier handling
             - Final tabular dataset ready

  Week 7-8:  First models + dashboard skeleton
             - Random Forest baseline (quick sanity check)
             - XGBoost + LightGBM with default params
             - Next.js project scaffolding
             - Mapbox GL + Deck.gl integration (terrain working)

Month 3 ──────────────────────────────────────────────────────
  Week 9-10: Model optimization + map generation
             - Optuna hyperparameter tuning (50+ trials/model)
             - Full SHAP analysis
             - Generate prediction grid (~500m across Córdoba)
             - Produce susceptibility GeoTIFF

  Week 11-12: Dashboard build
             - View 1: Risk extrusion over terrain
             - View 2: Hexbin aggregation
             - View 3: Heatmap + terrain flyover
             - View 4: Analysis panel with charts

Month 4 ──────────────────────────────────────────────────────
  Week 13-14: Validation + polish
             - Temporal validation (2023–2024 overlay)
             - Zonal accuracy statistics
             - Dashboard interactions, tooltips, responsive design
             - Deploy to Vercel

  Week 15-16: Paper writing
             - Introduction + literature review
             - Methodology section
             - Results + figures (map screenshots, SHAP plots,
               ROC curves, confusion matrices)
             - Discussion + conclusions

Month 5 (buffer) ─────────────────────────────────────────────
  - Paper revision + peer feedback from professor
  - Dashboard final polish
  - Presentation preparation
```

---

## 7. Paper Structure (Target: ~6,000–8,000 words)

1. **Introduction** — Wildfire problem in Argentina, motivation, gap in literature
2. **Study Area** — Córdoba Province: geography, climate, fire history, 2024 event
3. **Data and Methods**
   - 3.1 Fire occurrence data (MODIS FIRMS)
   - 3.2 Environmental features (table of all ~15 variables with sources)
   - 3.3 Sampling strategy (fire/non-fire point generation)
   - 3.4 Feature selection (VIF, correlation analysis)
   - 3.5 Machine learning models (RF, XGBoost, LightGBM)
   - 3.6 Hyperparameter optimization (Optuna)
   - 3.7 Evaluation metrics (AUC-ROC, accuracy, temporal validation)
   - 3.8 Model interpretability (SHAP)
4. **Results**
   - 4.1 Feature importance analysis
   - 4.2 Model comparison (table + ROC curves)
   - 4.3 Susceptibility map (the 3D visualization screenshots)
   - 4.4 Temporal validation (2023–2024 overlay)
5. **Discussion** — Compare with other regional studies, limitations, implications
6. **Conclusions** — Summary, policy recommendations, future work
7. **References** — ~40–60 citations

---

## 8. Key References to Follow as Templates

These recent papers (2024–2025) use essentially the same methodology you'll follow:

- **Germany** — "Machine learning wildfire susceptibility mapping for Germany" (Natural Hazards, 2025). Uses MODIS + ERA5-Land + Random Forest. 89% accuracy.
- **Algeria** — "ML-Based Wildfire Susceptibility Mapping: A GIS-Integrated Framework" (Applied Sciences, 2025). Uses MODIS + SRTM + ERA5 + OSM. XGBoost AUC = 0.96.
- **Russia** — "Exploration of geo-spatial data and ML algorithms for robust wildfire occurrence prediction" (Scientific Reports, 2025). Uses ERA5-Land + MODIS NDVI. Binary classification.
- **Turkey** — "A deep learning ensemble model for wildfire susceptibility mapping" (Ecological Informatics, 2021). MODIS active fire + 7 ML models.
- **Pakistan** — "ML-based forest fire vulnerability assessment" (Fire Ecology, 2025). MODIS FIRMS + topographic + climatic + human activity variables.

All of these are open access — read their methodology sections closely and follow the same structure.

---

## 9. Risk Mitigation

| Risk | Likelihood | Mitigation |
|---|---|---|
| MODIS has few detections for small fires | Medium | Use VIIRS (375m, 2012+) as supplement; acknowledge in limitations |
| ERA5-Land resolution (~9km) too coarse | Low | Standard in literature; supplement with NDVI/LST at 500m–1km |
| Córdoba has too few fire events for training | Low | MODIS 2001–2022 = 20+ years of data; province has high fire activity |
| Negative sampling introduces bias | Medium | Use stratified random sampling by land cover; sensitivity analysis |
| Deck.gl learning curve | Medium | Strong documentation; Gerardo has Mapbox experience from BA project |
| Paper rejected by journal | Low | Target university journal first; methodology is well-established |

---

## 10. Deliverables Checklist

- [ ] Clean tabular dataset (fire/non-fire points × features) — shareable CSV
- [ ] Trained models (RF, XGBoost, LightGBM) — MLflow artifacts
- [ ] Susceptibility GeoTIFF raster for Córdoba Province
- [ ] SHAP analysis plots (global bar, beeswarm, local waterfall)
- [ ] Interactive 3D dashboard deployed on Vercel
- [ ] Scientific article (6,000–8,000 words)
- [ ] GitHub repository with reproducible pipeline
- [ ] Presentation slides for university defense
