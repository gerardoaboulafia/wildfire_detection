# Wildfire Susceptibility Mapping - Cordoba Province, Argentina

Binary classification (fire/no-fire) using satellite fire detections and ~15 environmental features, trained with ensemble ML models, interpreted with SHAP, and visualized as a 3D interactive dashboard.

University research project — UCA (Universidad Catolica Argentina), Laboratorio III.

## Project Structure

```
notebooks/          # Jupyter notebooks (full pipeline)
src/                # Python source modules
scripts/            # Utility scripts
reusable_code/      # Adapted pipelines (GEE, SoilGrids, OSM)
configs/            # Project configuration (cordoba.yaml)
dashboard/          # Next.js 3D visualization app
tasks/              # Task tracking and lessons learned
data/               # Raw & processed data (gitignored)
models/             # Trained model artifacts (gitignored)
mlruns/             # MLflow experiment tracking (gitignored)
outputs/            # Generated maps and figures (gitignored)
```

## Pipeline

| Step | Notebook | Description |
|------|----------|-------------|
| 1 | `01_data_check` | Data ingestion and quality checks |
| 2 | `02_eda` | Exploratory data analysis |
| 3 | `03_preprocessing` / `03a` / `03b` | Feature engineering, resampling, VIF/correlation filtering |
| 4 | `04_modeling` | RF, XGBoost, LightGBM training with Optuna tuning |
| 4b | `04b_tuning_v2` | Hyperparameter tuning (50-100 trials) |
| 4c | `04c_shap_v2` | SHAP feature importance analysis |
| 4d | `04d_evaluation_v2` | Model evaluation and comparison |
| 4f | `04f_neural_network` | Neural network experiments (Colab) |
| 5a | `05a_prediction_grid` | ~500m susceptibility grid across Cordoba |
| 5b | `05b_validation` | Temporal validation with VIIRS 2023-2024 |

## Data Sources

| Data | Source | Resolution |
|------|--------|------------|
| Fire detections (training) | MODIS FIRMS MCD14ML | 1 km |
| Fire detections (validation) | VIIRS VNP14IMG | 375 m |
| Topography | SRTM DEM via GEE | 30 m |
| Vegetation indices | MODIS MOD13A1 via GEE | 500 m |
| Land surface temperature | MODIS MOD11A2 via GEE | 1 km |
| Climate | ERA5-Land via CDS API | ~9 km |
| Soil properties | SoilGrids | 250 m |
| Roads & rivers | OpenStreetMap via OSMnx | Vector |
| Population density | WorldPop | 100 m |
| Land cover | Copernicus Global | 100 m |

## Setup

### ML Pipeline (Python)

```bash
conda activate py311_ds
pip install -r requirements.txt
```

Data files are not included in the repo due to size (~2.5 GB). Each notebook documents how to fetch its data from the original sources (NASA FIRMS, Google Earth Engine, CDS API, SoilGrids, OSM).

### Dashboard (Next.js)

```bash
cd dashboard
npm install
```

Create `dashboard/.env.local`:

```
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here
```

```bash
npm run dev
```

See [`dashboard/README.md`](dashboard/README.md) for more details.

## Key Design Decisions

- **Binary target** from satellite fire detections — no discretization
- **Negative sampling**: >5 km from any fire detection, stratified by land cover
- **Primary metric**: AUC-ROC (standard in susceptibility mapping literature)
- **Risk classification**: Natural Breaks (Jenks) into 4 zones — Low, Moderate, High, Very High
- **Validation target**: >80% of actual fires in High/Very High zones
- **Temporal validation**: training on MODIS 2001-2022, validation on VIIRS 2023-2024

## Tech Stack

**ML**: scikit-learn, XGBoost, LightGBM, Optuna, SHAP, MLflow, GeoPandas, rasterio, xarray

**Dashboard**: Next.js 14, Deck.gl, Mapbox GL, Zustand, Recharts, Tailwind CSS
