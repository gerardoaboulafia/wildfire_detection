# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

- Python environment: conda env `py311_ds` — use this when running any Python scripts or notebooks
  - Activate with: `conda activate py311_ds`
  - Use as Jupyter kernel: `py311_ds`

## Project Overview

Wildfire susceptibility mapping for Córdoba Province, Argentina. Binary classification (fire/no-fire) using satellite fire detections and ~15 environmental features, trained with ensemble ML models (Random Forest, XGBoost, LightGBM), interpreted with SHAP, and visualized as a 3D interactive dashboard.

Outputs: scientific article for university journal + deployed 3D dashboard.

## Architecture

The project has two main components:

### 1. ML Pipeline (Python)
- **Data ingestion**: NASA FIRMS (MODIS/VIIRS fire detections), Google Earth Engine (NDVI, LST, DEM), ERA5-Land (climate), SoilGrids (soil), OSM/OSMnx (roads, rivers), WorldPop (population), Copernicus (land cover)
- **Feature extraction**: Raster value extraction at sample points, distance computations, terrain derivatives
- **Preprocessing**: VIF check (drop >10), correlation filter (r>0.85), StandardScaler, one-hot encoding for land cover, 70/30 stratified split
- **Modeling**: RF/XGBoost/LightGBM with Optuna tuning (50-100 trials), 10-fold stratified CV, MLflow tracking
- **Map generation**: ~500m prediction grid across Córdoba, output as GeoTIFF + GeoJSON
- **Training data**: MODIS FIRMS 2001-2022. **Validation**: VIIRS 2023-2024 (temporal, independent)

### 2. Visualization Dashboard (Next.js)
- **Stack**: Next.js 14 (App Router) + react-map-gl + Deck.gl + Zustand + Recharts/Plotly.js
- **Deployment**: Vercel
- **Views**: Risk extrusion over terrain (ColumnLayer), hexbin aggregation (HexagonLayer), terrain flyover with heatmap, analysis panel (SHAP plots, ROC curves, statistics)
- **Base map**: Mapbox GL with 3D terrain

## Key Design Decisions

- Binary target (fire/no-fire) from satellite detections — no discretization
- Negative samples must be >5km from any fire detection, stratified by land cover
- Primary metric: AUC-ROC (standard in susceptibility mapping literature)
- Zonal validation target: >80% of actual fires in High/Very High zones
- Risk classification uses Natural Breaks (Jenks) into 4 zones: Low, Moderate, High, Very High

## Data Sources Quick Reference

| Data | Source | Resolution |
|------|--------|------------|
| Fire detections (training) | MODIS FIRMS MCD14ML | 1 km |
| Fire detections (validation) | VIIRS VNP14IMG | 375 m |
| Topography | SRTM DEM via GEE | 30 m |
| Vegetation indices | MODIS MOD13A1 via GEE | 500 m |
| Climate | ERA5-Land via CDS | ~9 km |
| Soil | SoilGrids | 250 m |
| Roads/rivers | OSM via OSMnx | Vector |
| Population | WorldPop | 100 m |
| Land cover | Copernicus Global | 100 m |

## Reusable Code from Forest-Fire Project

Some pipelines are adapted from a prior project:
- `SoilGrids.py` — direct reuse, change coordinates to Córdoba
- `geospatial.py` — road/river distance computations via OSM
- `GEE.py` — adapt from weather queries to NDVI/LST extraction
- `feature_engine.py` — keep scaling/encoding, drop KMeans discretization
- MLflow infrastructure — direct reuse
- LightGBM/XGBoost modeling code — direct reuse

## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.