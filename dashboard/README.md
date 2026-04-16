# Wildfire Susceptibility Dashboard - Cordoba, Argentina

Interactive 3D dashboard for visualizing wildfire susceptibility across Cordoba Province, Argentina. Built as part of a university research project that uses ensemble ML models (Random Forest, XGBoost, LightGBM) trained on satellite fire detections and environmental features.

## Views

- **Risk Heatmap** - 3D extruded columns showing susceptibility probability across a ~500m prediction grid
- **Hexbin Aggregation** - Hexagonal binning of risk values for spatial pattern analysis
- **Terrain Flyover** - Animated camera flyover with heatmap overlay on 3D terrain
- **Analysis Panel** - SHAP feature importance plots, ROC curves, and model statistics

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **3D Mapping**: Mapbox GL + Deck.gl (ColumnLayer, HexagonLayer)
- **State**: Zustand
- **Charts**: Recharts
- **Styling**: Tailwind CSS
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+
- A [Mapbox access token](https://account.mapbox.com/access-tokens/)

### Setup

```bash
npm install
```

Create a `.env.local` file in the project root:

```
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token_here
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
src/
  app/              # Next.js App Router pages and layout
  components/
    charts/         # Recharts-based data visualizations
    controls/       # UI controls (basemap selector, etc.)
    layers/         # Deck.gl layer hooks (grid, zones)
    views/          # Main dashboard views (Risk, Hexbin, Flyover, Analysis)
    ui/             # Reusable UI components
    Dashboard.tsx   # Root dashboard layout
    MapContainer.tsx# Mapbox + Deck.gl map initialization
    Sidebar.tsx     # Navigation sidebar
  hooks/            # Custom React hooks
  lib/              # Constants and utilities
  store/            # Zustand state management
public/
  data/             # Pre-computed model outputs (grid, zones, SHAP, stats)
```

## Data

The dashboard consumes pre-computed outputs from the ML pipeline:

| File | Description |
|------|-------------|
| `grid.bin` / `grid_meta.json` | ~500m prediction grid with susceptibility probabilities |
| `zones_simplified.geojson` | Risk zones (Low, Moderate, High, Very High) via Natural Breaks |
| `fires.bin` / `fires_meta.json` | Historical fire detections (MODIS FIRMS) |
| `shap_global.json` / `shap_samples.json` | SHAP feature importance values |
| `roc_curves.png` | Model ROC curves |
| `stats.json` | Model performance metrics |
| `annual_fires.json` | Year-by-year fire counts |

## License

University project - UCA (Universidad Catolica Argentina), Laboratorio III.
