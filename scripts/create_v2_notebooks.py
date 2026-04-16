"""
Creates three notebooks for the v2 re-sampling pipeline:
  notebooks/03a_resampling.ipynb
  notebooks/03b_preprocessing_v2.ipynb
  notebooks/04_modeling_v2.ipynb
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def code_cell(source, cell_id):
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


def md_cell(source, cell_id):
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": source,
    }


def notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "py311_ds",
                "language": "python",
                "name": "py311_ds",
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def save(nb, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
    print(f"Saved: {path}")


# ===========================================================================
# 03a_resampling.ipynb
# ===========================================================================

def make_03a():
    cells = []

    cells.append(md_cell(
        "# 03a — Elevation-Stratified Resampling (v2)\n\n"
        "Fixes geographic confounding by generating negatives that span the **same elevation "
        "distribution** as fire points.\n\n"
        "**Key changes vs v1:**\n"
        "- Buffer reduced: 5 km → 1 km\n"
        "- Joint stratification: elevation band × land cover class\n"
        "- Negatives now appear *inside* the Sierras de Córdoba, not just on the flat plains\n\n"
        "**Outputs:**\n"
        "- `data/processed/sample_points_v2.gpkg`\n"
        "- `data/processed/dataset_v2.csv`",
        "cell-00",
    ))

    cells.append(code_cell(
        "import sys\n"
        "import warnings\n"
        "from pathlib import Path\n"
        "from collections import Counter, defaultdict\n"
        "\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import geopandas as gpd\n"
        "import rasterio\n"
        "import shapely\n"
        "from scipy.spatial import cKDTree\n"
        "from scipy.stats import ks_2samp\n"
        "from shapely.geometry import Point\n"
        "import matplotlib\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "\n"
        "warnings.filterwarnings('ignore')\n"
        "sns.set_theme(style='whitegrid', font_scale=1.1)\n"
        "matplotlib.rcParams['figure.dpi'] = 120\n"
        "\n"
        "ROOT      = Path('..').resolve()\n"
        "RAW       = ROOT / 'data' / 'raw'\n"
        "PROCESSED = ROOT / 'data' / 'processed'\n"
        "OUTPUTS   = ROOT / 'outputs'\n"
        "OUTPUTS.mkdir(exist_ok=True)\n"
        "\n"
        "CRS_WGS84  = 'EPSG:4326'\n"
        "CRS_METRIC = 'EPSG:32720'  # UTM Zone 20S\n"
        "\n"
        "GRID_SIZE_M   = 500       # 500m dedup grid (matches MODIS)\n"
        "NEG_BUFFER_M  = 1_000     # 1km exclusion buffer (was 5km in v1)\n"
        "BATCH_SIZE    = 150_000\n"
        "OVERSAMPLE    = 6         # Generate 6× candidates for stratification\n"
        "RANDOM_SEED   = 42\n"
        "N_ELEV_BANDS  = 5\n"
        "\n"
        "print('Setup complete.')",
        "cell-01",
    ))

    cells.append(md_cell("## 1. Load Boundary & Fire Points — Deduplicate", "cell-02"))

    cells.append(code_cell(
        "# Load Córdoba boundary\n"
        "boundary_gdf = gpd.read_file(RAW / 'cordoba_boundary.shp').to_crs(CRS_WGS84)\n"
        "boundary_poly = boundary_gdf.geometry.union_all()\n"
        "bbox = boundary_poly.bounds\n"
        "minx, miny, maxx, maxy = bbox\n"
        "print(f'Boundary bbox: {bbox}')\n"
        "\n"
        "# Load raw MODIS fire detections\n"
        "fire_raw = gpd.read_file(PROCESSED / 'firms_modis.gpkg').to_crs(CRS_WGS84)\n"
        "print(f'Raw MODIS detections: {len(fire_raw):,}')\n"
        "\n"
        "# Deduplicate to 500m UTM grid (same logic as sampling.py)\n"
        "fire_utm = fire_raw.to_crs(CRS_METRIC)\n"
        "easting  = fire_utm.geometry.x.values\n"
        "northing = fire_utm.geometry.y.values\n"
        "cell_x   = (easting  // GRID_SIZE_M).astype(np.int64)\n"
        "cell_y   = (northing // GRID_SIZE_M).astype(np.int64)\n"
        "\n"
        "df_grid = pd.DataFrame({\n"
        "    'cell_x': cell_x, 'cell_y': cell_y,\n"
        "    'easting': easting, 'northing': northing,\n"
        "    'date': fire_raw['date'].values,\n"
        "})\n"
        "dedup = (\n"
        "    df_grid.groupby(['cell_x', 'cell_y'])\n"
        "    .agg(easting=('easting', 'mean'), northing=('northing', 'mean'), date=('date', 'first'))\n"
        "    .reset_index(drop=True)\n"
        ")\n"
        "\n"
        "geom_utm = [Point(e, n) for e, n in zip(dedup.easting, dedup.northing)]\n"
        "pos_utm  = gpd.GeoDataFrame({'date': dedup.date}, geometry=geom_utm, crs=CRS_METRIC)\n"
        "pos_gdf  = pos_utm.to_crs(CRS_WGS84)\n"
        "pos_gdf['label'] = 1\n"
        "pos_gdf['lat']   = pos_gdf.geometry.y\n"
        "pos_gdf['lon']   = pos_gdf.geometry.x\n"
        "pos_gdf['month'] = pd.to_datetime(pos_gdf['date']).dt.month.astype('Int64')\n"
        "pos_gdf = pos_gdf.reset_index(drop=True)\n"
        "\n"
        "n_positive = len(pos_gdf)\n"
        "print(f'After 500m grid dedup: {n_positive:,} unique fire cells')",
        "cell-03",
    ))

    cells.append(md_cell("## 2. Extract Fire-Point Elevations & Define Bands", "cell-04"))

    cells.append(code_cell(
        "# Extract elevation at deduplicated fire points\n"
        "dem_path = RAW / 'dem' / 'elevation.tif'\n"
        "with rasterio.open(dem_path) as src:\n"
        "    dem_nodata = src.nodata\n"
        "    elev_fire  = np.array([v[0] for v in src.sample(zip(pos_gdf.lon, pos_gdf.lat))], dtype=float)\n"
        "\n"
        "if dem_nodata is not None:\n"
        "    elev_fire[elev_fire == dem_nodata] = np.nan\n"
        "elev_fire[elev_fire <= -9000] = np.nan\n"
        "\n"
        "valid_elev = elev_fire[~np.isnan(elev_fire)]\n"
        "print(f'Fire elevation — min: {valid_elev.min():.0f}m  '\n"
        "      f'median: {np.median(valid_elev):.0f}m  max: {valid_elev.max():.0f}m')\n"
        "print(f'NaN elevations: {np.isnan(elev_fire).sum()}')\n"
        "\n"
        "fig, ax = plt.subplots(figsize=(8, 4))\n"
        "ax.hist(valid_elev, bins=50, color='firebrick', alpha=0.75, edgecolor='white', linewidth=0.4)\n"
        "ax.set_xlabel('Elevation (m)')\n"
        "ax.set_ylabel('Count')\n"
        "ax.set_title('Fire Point Elevation Distribution (deduplicated)')\n"
        "ax.grid(alpha=0.3)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_fire_elevation_histogram.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-05",
    ))

    cells.append(code_cell(
        "# Define N_ELEV_BANDS quantile-based elevation bands from fire points\n"
        "q_edges = np.linspace(0, 1, N_ELEV_BANDS + 1)\n"
        "band_edges = np.quantile(valid_elev, q_edges)\n"
        "\n"
        "# Ensure strictly increasing edges (handle flat quantiles)\n"
        "if len(np.unique(band_edges)) < len(band_edges):\n"
        "    print('Warning: duplicate quantile edges — using linspace fallback')\n"
        "    band_edges = np.linspace(valid_elev.min(), valid_elev.max(), N_ELEV_BANDS + 1)\n"
        "\n"
        "# internal_edges used for np.digitize (excludes min/max)\n"
        "internal_edges = band_edges[1:-1]\n"
        "\n"
        "print(f'Elevation bands ({N_ELEV_BANDS} quantile-based):')\n"
        "for i in range(N_ELEV_BANDS):\n"
        "    fire_in_band = ((valid_elev >= band_edges[i]) & (valid_elev < band_edges[i+1])).sum()\n"
        "    print(f'  Band {i}: {band_edges[i]:6.0f} – {band_edges[i+1]:6.0f} m  '\n"
        "          f'({fire_in_band:,} fire pts)')",
        "cell-06",
    ))

    cells.append(md_cell("## 3. Compute Joint Strata (Elevation Band × Land Cover) from Fire Points", "cell-07"))

    cells.append(code_cell(
        "# Read land cover at fire points\n"
        "lc_path = RAW / 'landcover.tif'\n"
        "with rasterio.open(lc_path) as src:\n"
        "    lc_fire = np.array([v[0] for v in src.sample(zip(pos_gdf.lon, pos_gdf.lat))], dtype=int)\n"
        "\n"
        "# Assign elevation band to each fire point (0 … N_ELEV_BANDS-1)\n"
        "elev_bands_fire = np.digitize(elev_fire, internal_edges).astype(int)\n"
        "# Assign NaN-elevation points to band 0\n"
        "elev_bands_fire = np.where(np.isnan(elev_fire), 0, elev_bands_fire).astype(int)\n"
        "elev_bands_fire = np.clip(elev_bands_fire, 0, N_ELEV_BANDS - 1)\n"
        "\n"
        "# Count per (elev_band, lc_class) stratum\n"
        "strata_fire   = list(zip(elev_bands_fire.tolist(), lc_fire.tolist()))\n"
        "strata_counts = Counter(strata_fire)\n"
        "total_fire    = len(strata_fire)\n"
        "\n"
        "print(f'Top-15 fire strata (elev_band, lc_class) → count:')\n"
        "for s, cnt in sorted(strata_counts.items(), key=lambda x: -x[1])[:15]:\n"
        "    print(f'  {str(s):20s}: {cnt:5,}  ({cnt/total_fire*100:.1f}%)')\n"
        "print(f'  ... ({len(strata_counts)} unique strata total)')\n"
        "\n"
        "# Target per stratum for negatives (proportional to fire distribution)\n"
        "strata_targets = {s: max(1, round(cnt / total_fire * n_positive))\n"
        "                  for s, cnt in strata_counts.items()}\n"
        "\n"
        "# Adjust rounding to hit exactly n_positive\n"
        "diff = n_positive - sum(strata_targets.values())\n"
        "if diff != 0:\n"
        "    top_s = max(strata_counts, key=strata_counts.get)\n"
        "    strata_targets[top_s] += diff\n"
        "\n"
        "print(f'\\nTotal target negatives: {sum(strata_targets.values()):,}  (n_positive={n_positive:,})')",
        "cell-08",
    ))

    cells.append(md_cell("## 4. Generate Negative Candidates (1 km Buffer Rejection Sampling)", "cell-09"))

    cells.append(code_cell(
        "# Build exclusion tree: all MODIS + VIIRS fire detections in UTM\n"
        "print('Building fire exclusion tree (MODIS + VIIRS)...')\n"
        "all_fire_gdfs = []\n"
        "for fname in ('firms_modis.gpkg', 'firms_viirs.gpkg'):\n"
        "    p = PROCESSED / fname\n"
        "    if p.exists():\n"
        "        all_fire_gdfs.append(gpd.read_file(p).to_crs(CRS_METRIC))\n"
        "\n"
        "combined_geom   = pd.concat([g.geometry for g in all_fire_gdfs])\n"
        "fire_coords_utm = np.column_stack([combined_geom.x, combined_geom.y])\n"
        "fire_tree       = cKDTree(fire_coords_utm)\n"
        "print(f'  {len(fire_coords_utm):,} detections in exclusion index')\n"
        "\n"
        "# Rejection sampling\n"
        "rng = np.random.default_rng(RANDOM_SEED)\n"
        "needed = n_positive * OVERSAMPLE\n"
        "candidates_lon, candidates_lat = [], []\n"
        "\n"
        "print(f'\\nGenerating ~{needed:,} candidates (buffer={NEG_BUFFER_M/1000:.0f} km)...')\n"
        "for iteration in range(60):\n"
        "    if len(candidates_lon) >= needed:\n"
        "        break\n"
        "\n"
        "    lons_b = rng.uniform(minx, maxx, BATCH_SIZE)\n"
        "    lats_b = rng.uniform(miny, maxy, BATCH_SIZE)\n"
        "\n"
        "    # Filter: inside boundary (vectorized shapely)\n"
        "    inside = shapely.contains_xy(boundary_poly, lons_b, lats_b)\n"
        "    lons_b, lats_b = lons_b[inside], lats_b[inside]\n"
        "    if len(lons_b) == 0:\n"
        "        continue\n"
        "\n"
        "    # Filter: > NEG_BUFFER_M from any fire (UTM distance)\n"
        "    pts_gdf    = gpd.GeoSeries(gpd.points_from_xy(lons_b, lats_b), crs=CRS_WGS84).to_crs(CRS_METRIC)\n"
        "    coords_utm = np.column_stack([pts_gdf.x, pts_gdf.y])\n"
        "    dists, _   = fire_tree.query(coords_utm, k=1, workers=-1)\n"
        "    far        = dists > NEG_BUFFER_M\n"
        "\n"
        "    candidates_lon.extend(lons_b[far].tolist())\n"
        "    candidates_lat.extend(lats_b[far].tolist())\n"
        "    pct = min(len(candidates_lon) / needed * 100, 100)\n"
        "    print(f'  Iter {iteration+1:2d}: +{far.sum():,} → {len(candidates_lon):,} total ({pct:.0f}%)')\n"
        "\n"
        "if len(candidates_lon) < n_positive:\n"
        "    raise RuntimeError(f'Only {len(candidates_lon):,} candidates — increase max iterations')\n"
        "print(f'\\nTotal candidates: {len(candidates_lon):,}')",
        "cell-10",
    ))

    cells.append(md_cell("## 5. Stratified Selection from Candidates", "cell-11"))

    cells.append(code_cell(
        "cand_lons = np.array(candidates_lon)\n"
        "cand_lats = np.array(candidates_lat)\n"
        "\n"
        "# Read elevation + LC at all candidates\n"
        "print(f'Reading elevation at {len(cand_lons):,} candidates...')\n"
        "with rasterio.open(dem_path) as src:\n"
        "    dem_nodata  = src.nodata\n"
        "    cand_elev   = np.array([v[0] for v in src.sample(zip(cand_lons, cand_lats))], dtype=float)\n"
        "if dem_nodata is not None:\n"
        "    cand_elev[cand_elev == dem_nodata] = np.nan\n"
        "cand_elev[cand_elev <= -9000] = np.nan\n"
        "\n"
        "print(f'Reading land cover at {len(cand_lons):,} candidates...')\n"
        "with rasterio.open(lc_path) as src:\n"
        "    cand_lc = np.array([v[0] for v in src.sample(zip(cand_lons, cand_lats))], dtype=int)\n"
        "\n"
        "# Drop invalid-elevation candidates\n"
        "valid = ~np.isnan(cand_elev)\n"
        "cand_lons, cand_lats = cand_lons[valid], cand_lats[valid]\n"
        "cand_elev, cand_lc   = cand_elev[valid], cand_lc[valid]\n"
        "print(f'Valid candidates after NaN filter: {len(cand_lons):,}')\n"
        "\n"
        "# Assign elevation bands to candidates\n"
        "cand_elev_bands = np.digitize(cand_elev, internal_edges).astype(int)\n"
        "cand_elev_bands = np.clip(cand_elev_bands, 0, N_ELEV_BANDS - 1)\n"
        "\n"
        "print('\\nCandidate elevation distribution:')\n"
        "for b in range(N_ELEV_BANDS):\n"
        "    cnt = (cand_elev_bands == b).sum()\n"
        "    print(f'  Band {b} ({band_edges[b]:.0f}–{band_edges[b+1]:.0f}m): {cnt:,} ({cnt/len(cand_elev_bands)*100:.1f}%)')\n"
        "\n"
        "# Index candidates by stratum\n"
        "stratum_indices = defaultdict(list)\n"
        "for idx, (eb, lc) in enumerate(zip(cand_elev_bands.tolist(), cand_lc.tolist())):\n"
        "    stratum_indices[(int(eb), int(lc))].append(idx)\n"
        "\n"
        "# Proportional sampling per stratum\n"
        "selected_idx = []\n"
        "missing_strata = []\n"
        "for stratum, target in sorted(strata_targets.items(), key=lambda x: -x[1]):\n"
        "    avail = stratum_indices.get(stratum, [])\n"
        "    if not avail:\n"
        "        missing_strata.append(stratum)\n"
        "        continue\n"
        "    take   = min(target, len(avail))\n"
        "    chosen = rng.choice(avail, take, replace=False).tolist()\n"
        "    selected_idx.extend(chosen)\n"
        "\n"
        "if missing_strata:\n"
        "    print(f'\\nStrata with no candidates (will fill from leftover): {len(missing_strata)}')\n"
        "\n"
        "# Fill any shortfall with random remaining candidates\n"
        "selected_set = set(selected_idx)\n"
        "shortfall    = n_positive - len(selected_set)\n"
        "if shortfall > 0:\n"
        "    leftover = [i for i in range(len(cand_lons)) if i not in selected_set]\n"
        "    if len(leftover) >= shortfall:\n"
        "        extra = rng.choice(leftover, shortfall, replace=False).tolist()\n"
        "        selected_idx.extend(extra)\n"
        "        print(f'Filled shortfall: +{shortfall} random candidates')\n"
        "    else:\n"
        "        print(f'WARNING: only {len(leftover)} leftover, shortfall={shortfall}')\n"
        "\n"
        "selected_idx = list(dict.fromkeys(selected_idx))[:n_positive]\n"
        "print(f'\\nFinal negative count: {len(selected_idx):,}  (target: {n_positive:,})')\n"
        "\n"
        "neg_lons = cand_lons[selected_idx]\n"
        "neg_lats = cand_lats[selected_idx]\n"
        "neg_lc   = cand_lc[selected_idx]\n"
        "neg_elev = cand_elev[selected_idx]",
        "cell-12",
    ))

    cells.append(md_cell("## 6. Diagnostic Plots", "cell-13"))

    cells.append(code_cell(
        "# Load old negatives for comparison\n"
        "old_samples = gpd.read_file(PROCESSED / 'sample_points.gpkg').to_crs(CRS_WGS84)\n"
        "old_neg     = old_samples[old_samples.label == 0].copy()\n"
        "\n"
        "# Read elevation at old negatives\n"
        "with rasterio.open(dem_path) as src:\n"
        "    dem_nodata   = src.nodata\n"
        "    elev_old_neg = np.array([v[0] for v in src.sample(zip(old_neg.lon, old_neg.lat))], dtype=float)\n"
        "if dem_nodata is not None:\n"
        "    elev_old_neg[elev_old_neg == dem_nodata] = np.nan\n"
        "elev_old_neg[elev_old_neg <= -9000] = np.nan\n"
        "elev_old_neg = elev_old_neg[~np.isnan(elev_old_neg)]\n"
        "\n"
        "# --- Plot 1: Elevation histograms ---\n"
        "fig, axes = plt.subplots(1, 3, figsize=(15, 4))\n"
        "xmax = valid_elev.max() + 100\n"
        "for ax, data, label, color in [\n"
        "    (axes[0], valid_elev,    'Fire points (positives)',          'firebrick'),\n"
        "    (axes[1], elev_old_neg,  'Old negatives (v1, 5 km buffer)',  'steelblue'),\n"
        "    (axes[2], neg_elev,      'New negatives (v2, 1 km + strat)', 'seagreen'),\n"
        "]:\n"
        "    ax.hist(data, bins=50, color=color, alpha=0.75, edgecolor='white', linewidth=0.4)\n"
        "    ax.set_xlabel('Elevation (m)')\n"
        "    ax.set_ylabel('Count')\n"
        "    ax.set_title(label)\n"
        "    ax.set_xlim(-50, xmax)\n"
        "    ax.grid(alpha=0.3)\n"
        "plt.suptitle('Elevation Distribution Comparison', y=1.02, fontsize=13)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_elevation_comparison.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()\n"
        "\n"
        "# KS-test: fire elevations vs new negatives\n"
        "ks_stat, ks_pval = ks_2samp(valid_elev, neg_elev)\n"
        "print(f'KS test (fire vs new negatives): stat={ks_stat:.3f}, p={ks_pval:.4f}')\n"
        "print('Result:', 'PASS (distributions overlap, p > 0.05)' if ks_pval > 0.05\n"
        "       else 'FAIL — distributions still differ significantly')",
        "cell-14",
    ))

    cells.append(code_cell(
        "# --- Plot 2: Spatial scatter ---\n"
        "fig, axes = plt.subplots(1, 2, figsize=(16, 7))\n"
        "for ax, n_lons, n_lats, title in [\n"
        "    (axes[0], old_neg.lon.values, old_neg.lat.values,\n"
        "     'Old negatives (v1 — 5 km buffer, plains only)'),\n"
        "    (axes[1], neg_lons, neg_lats,\n"
        "     'New negatives (v2 — 1 km buffer + elev stratified)'),\n"
        "]:\n"
        "    ax.scatter(n_lons, n_lats, s=0.4, alpha=0.3, c='steelblue', label='Negatives')\n"
        "    ax.scatter(pos_gdf.lon, pos_gdf.lat, s=0.4, alpha=0.3, c='firebrick', label='Fires')\n"
        "    ax.set_xlabel('Longitude')\n"
        "    ax.set_ylabel('Latitude')\n"
        "    ax.set_title(title, fontsize=10)\n"
        "    ax.legend(markerscale=6, fontsize=9)\n"
        "    ax.set_aspect('equal')\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_spatial_scatter_comparison.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-15",
    ))

    cells.append(md_cell("## 7. Build GeoDataFrame & Save `sample_points_v2.gpkg`", "cell-16"))

    cells.append(code_cell(
        "# Add land cover to positive samples\n"
        "with rasterio.open(lc_path) as src:\n"
        "    pos_lc = np.array([v[0] for v in src.sample(zip(pos_gdf.lon, pos_gdf.lat))], dtype=int)\n"
        "pos_gdf['land_cover_class'] = pos_lc\n"
        "\n"
        "# Build negative GeoDataFrame\n"
        "neg_gdf = gpd.GeoDataFrame(\n"
        "    {\n"
        "        'label'           : np.zeros(len(neg_lons), dtype=int),\n"
        "        'lat'             : neg_lats,\n"
        "        'lon'             : neg_lons,\n"
        "        'land_cover_class': neg_lc.astype(int),\n"
        "        'date'            : pd.NaT,\n"
        "        'month'           : pd.array([9] * len(neg_lons), dtype='Int64'),\n"
        "    },\n"
        "    geometry=gpd.points_from_xy(neg_lons, neg_lats),\n"
        "    crs=CRS_WGS84,\n"
        ")\n"
        "\n"
        "# Combine, shuffle, save\n"
        "combined_v2 = gpd.GeoDataFrame(\n"
        "    pd.concat([pos_gdf, neg_gdf], ignore_index=True), crs=CRS_WGS84\n"
        ")\n"
        "combined_v2 = combined_v2.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)\n"
        "\n"
        "out_path = PROCESSED / 'sample_points_v2.gpkg'\n"
        "combined_v2.to_file(out_path, driver='GPKG')\n"
        "\n"
        "print(f'Saved: {out_path}')\n"
        "print(f'Total  : {len(combined_v2):,}')\n"
        "print(f'Fires  : {int(combined_v2.label.sum()):,}')\n"
        "print(f'No-fire: {int((combined_v2.label == 0).sum()):,}')\n"
        "print(f'Balance: {combined_v2.label.mean():.3f}')",
        "cell-17",
    ))

    cells.append(md_cell("## 8. Feature Extraction → `dataset_v2.csv`", "cell-18"))

    cells.append(code_cell(
        "# Import extraction functions from data/processing/extract_features.py\n"
        "sys.path.insert(0, str(ROOT / 'data' / 'processing'))\n"
        "import importlib\n"
        "import extract_features as ef\n"
        "importlib.reload(ef)\n"
        "\n"
        "samples_v2 = combined_v2.copy()\n"
        "lons_v2    = samples_v2['lon'].values\n"
        "lats_v2    = samples_v2['lat'].values\n"
        "\n"
        "print('=' * 60)\n"
        "print('Feature Extraction — v2 sample points')\n"
        "print('=' * 60)\n"
        "\n"
        "# 1. Raster features\n"
        "print('\\n[1/4] Raster features...')\n"
        "raster_df = ef.extract_raster_features(lons_v2, lats_v2)\n"
        "\n"
        "# 2. Aggregate soil depth layers\n"
        "print('\\n[2/4] Aggregating soil depths...')\n"
        "raster_df = ef.aggregate_soil_depths(raster_df)\n"
        "\n"
        "# 3. OSM distances (uses cached files in data/raw/osm/)\n"
        "print('\\n[3/4] OSM vector distances (cached)...')\n"
        "osm_vectors = ef.get_osm_vectors(boundary_poly, bbox)\n"
        "osm_df      = ef.compute_osm_distances(lons_v2, lats_v2, osm_vectors)\n"
        "\n"
        "# 4. Temporal features\n"
        "print('\\n[4/4] Temporal features...')\n"
        "months_v2 = samples_v2['month'].astype('Int64').reset_index(drop=True)\n"
        "temp_df   = ef.compute_temporal_features(months_v2)\n"
        "\n"
        "# Assemble\n"
        "print('\\nAssembling dataset_v2...')\n"
        "dataset_v2 = pd.concat([\n"
        "    samples_v2[['lat', 'lon', 'label', 'month', 'land_cover_class']].reset_index(drop=True),\n"
        "    raster_df.drop(columns=['land_cover_class'], errors='ignore').reset_index(drop=True),\n"
        "    osm_df.reset_index(drop=True),\n"
        "    temp_df.reset_index(drop=True),\n"
        "], axis=1)\n"
        "\n"
        "# Use LC from raster extraction (authoritative)\n"
        "if 'land_cover_class' in raster_df.columns:\n"
        "    dataset_v2['land_cover_class'] = raster_df['land_cover_class'].values\n"
        "\n"
        "out_path = PROCESSED / 'dataset_v2.csv'\n"
        "dataset_v2.to_csv(out_path, index=False)\n"
        "\n"
        "print(f'\\nSaved: {out_path}')\n"
        "print(f'Shape: {dataset_v2.shape}')\n"
        "print(f'Class balance: {dataset_v2.label.mean():.3f}')\n"
        "null_counts = dataset_v2.isnull().sum()\n"
        "if null_counts.any():\n"
        "    print('\\nNull counts:')\n"
        "    for col, n in null_counts[null_counts > 0].items():\n"
        "        print(f'  {col}: {n}')",
        "cell-19",
    ))

    cells.append(md_cell("## 9. Verification", "cell-20"))

    cells.append(code_cell(
        "print('=== RESAMPLING VERIFICATION ===')\n"
        "\n"
        "# 1. Sample count matches 1:1\n"
        "assert combined_v2.label.sum() == (combined_v2.label == 0).sum(), 'Imbalanced sample'\n"
        "print(f'  [OK] Balanced 1:1 — {n_positive:,} fires, {n_positive:,} negatives')\n"
        "\n"
        "# 2. KS-test: fire vs new-negatives elevation (expect p > 0.05)\n"
        "ks_stat2, ks_pval2 = ks_2samp(valid_elev, neg_elev)\n"
        "symbol = 'OK' if ks_pval2 > 0.05 else 'FAIL'\n"
        "print(f'  [{symbol}] KS-test elevation overlap: stat={ks_stat2:.3f}, p={ks_pval2:.4f} '\n"
        "      f'(target p > 0.05)')\n"
        "\n"
        "# 3. Negatives span mountain zone (some elevation > 500m)\n"
        "neg_high = (neg_elev > 500).sum()\n"
        "print(f'  [OK] Negatives > 500m elevation: {neg_high:,} ({neg_high/len(neg_elev)*100:.1f}%)')\n"
        "\n"
        "# 4. Old negatives barely had any > 500m\n"
        "old_high = (elev_old_neg > 500).sum()\n"
        "print(f'  [INFO] Old negatives > 500m: {old_high:,} ({old_high/len(elev_old_neg)*100:.1f}%) '\n"
        "        f'(should be much lower)')\n"
        "\n"
        "# 5. dataset_v2.csv saved\n"
        "assert (PROCESSED / 'dataset_v2.csv').exists()\n"
        "print(f'  [OK] dataset_v2.csv saved ({len(dataset_v2):,} rows)')\n"
        "\n"
        "print('\\nResampling v2 complete. Run 03b_preprocessing_v2.ipynb next.')",
        "cell-21",
    ))

    return notebook(cells)


# ===========================================================================
# 03b_preprocessing_v2.ipynb
# ===========================================================================

def make_03b():
    cells = []

    cells.append(md_cell(
        "# 03b — Preprocessing v2 (Spatial Block Split)\n\n"
        "Input: `data/processed/dataset_v2.csv`\n\n"
        "Changes vs v1:\n"
        "- Uses elevation-stratified negative samples\n"
        "- Adds **spatial block IDs** (20 km UTM grid)\n"
        "- `GroupShuffleSplit` ensures no spatial block leaks between train/test\n\n"
        "Outputs: `train_v2.csv`, `test_v2.csv`, `scaler_v2.pkl`, `encoder_v2.pkl`, `selected_features_v2.json`",
        "cell-00",
    ))

    cells.append(code_cell(
        "import warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "\n"
        "import json\n"
        "import pickle\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import geopandas as gpd\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "from pathlib import Path\n"
        "\n"
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder\n"
        "from sklearn.model_selection import GroupShuffleSplit\n"
        "from statsmodels.stats.outliers_influence import variance_inflation_factor\n"
        "\n"
        "sns.set_theme(style='whitegrid', font_scale=1.1)\n"
        "\n"
        "PROCESSED = Path('../data/processed')\n"
        "OUTPUTS   = Path('../outputs')\n"
        "OUTPUTS.mkdir(exist_ok=True)\n"
        "\n"
        "RANDOM_STATE   = 42\n"
        "VIF_THRESHOLD  = 10.0\n"
        "CORR_THRESHOLD = 0.85\n"
        "TEST_SIZE      = 0.30\n"
        "BLOCK_SIZE_M   = 20_000  # 20 km spatial blocks\n"
        "\n"
        "df = pd.read_csv(PROCESSED / 'dataset_v2.csv')\n"
        "print(f'Loaded dataset_v2: {df.shape}')\n"
        "print(f'Class balance: {df.label.mean():.4f}')",
        "cell-01",
    ))

    cells.append(md_cell("## 1. Missing Value Imputation", "cell-02"))

    cells.append(code_cell(
        "pop_median = df['population_density'].median()\n"
        "df['population_density'] = df['population_density'].fillna(pop_median)\n"
        "print(f'population_density: filled NaN with median={pop_median:.4f}')\n"
        "assert df.isnull().sum().sum() == 0, 'Unexpected NaN remaining'\n"
        "print('No remaining NaN values.')",
        "cell-03",
    ))

    cells.append(md_cell("## 2. Assign Spatial Block IDs", "cell-04"))

    cells.append(code_cell(
        "# Convert lat/lon to UTM 20S, snap to 20km grid → block_id\n"
        "pts_gdf = gpd.GeoDataFrame(\n"
        "    geometry=gpd.points_from_xy(df['lon'].values, df['lat'].values),\n"
        "    crs='EPSG:4326'\n"
        ").to_crs('EPSG:32720')\n"
        "\n"
        "block_x = (pts_gdf.geometry.x // BLOCK_SIZE_M).astype(int)\n"
        "block_y = (pts_gdf.geometry.y // BLOCK_SIZE_M).astype(int)\n"
        "df['block_id'] = block_x.astype(str) + '_' + block_y.astype(str)\n"
        "\n"
        "n_blocks = df['block_id'].nunique()\n"
        "print(f'Spatial blocks (20km grid): {n_blocks} unique blocks')\n"
        "print(f'Samples per block — median: {df.groupby(\"block_id\").size().median():.0f}  '\n"
        "      f'min: {df.groupby(\"block_id\").size().min()}  '\n"
        "      f'max: {df.groupby(\"block_id\").size().max()}')\n"
        "\n"
        "# Spatial distribution of blocks\n"
        "fig, ax = plt.subplots(figsize=(8, 7))\n"
        "scatter = ax.scatter(\n"
        "    df['lon'], df['lat'],\n"
        "    c=pd.factorize(df['block_id'])[0],\n"
        "    s=0.5, alpha=0.4, cmap='tab20'\n"
        ")\n"
        "ax.set_title(f'Spatial Blocks (20 km grid) — {n_blocks} blocks', fontsize=12)\n"
        "ax.set_xlabel('Longitude')\n"
        "ax.set_ylabel('Latitude')\n"
        "ax.set_aspect('equal')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../outputs/v2_spatial_blocks.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-05",
    ))

    cells.append(md_cell("## 3. VIF-based Multicollinearity Filter", "cell-06"))

    cells.append(code_cell(
        "EXCLUDE_FROM_VIF = {'lat', 'lon', 'label', 'month', 'land_cover_class',\n"
        "                    'fire_season_flag', 'block_id'}\n"
        "\n"
        "def compute_vif(data: pd.DataFrame) -> pd.DataFrame:\n"
        "    vif_data = pd.DataFrame()\n"
        "    vif_data['feature'] = data.columns\n"
        "    vif_data['VIF'] = [\n"
        "        variance_inflation_factor(data.values, i)\n"
        "        for i in range(data.shape[1])\n"
        "    ]\n"
        "    return vif_data.sort_values('VIF', ascending=False).reset_index(drop=True)\n"
        "\n"
        "\n"
        "def iterative_vif_filter(df, threshold):\n"
        "    keep = [c for c in df.columns if c not in EXCLUDE_FROM_VIF]\n"
        "    dropped = []\n"
        "    iteration = 0\n"
        "    while True:\n"
        "        vif = compute_vif(df[keep])\n"
        "        max_vif = vif['VIF'].max()\n"
        "        if max_vif <= threshold:\n"
        "            break\n"
        "        worst = vif.loc[vif['VIF'].idxmax(), 'feature']\n"
        "        print(f'  Iter {iteration+1}: drop \"{worst}\" (VIF={max_vif:.2f})')\n"
        "        keep.remove(worst)\n"
        "        dropped.append(worst)\n"
        "        iteration += 1\n"
        "    return keep, dropped\n"
        "\n"
        "\n"
        "print(f'VIF filter (threshold={VIF_THRESHOLD})...')\n"
        "initial_numeric = [c for c in df.columns if c not in EXCLUDE_FROM_VIF]\n"
        "print(f'Initial numeric features: {len(initial_numeric)}')\n"
        "\n"
        "initial_vif = compute_vif(df[initial_numeric])\n"
        "print('\\nInitial VIF values:')\n"
        "print(initial_vif.to_string(index=False))",
        "cell-07",
    ))

    cells.append(code_cell(
        "kept_features, dropped_vif = iterative_vif_filter(df, VIF_THRESHOLD)\n"
        "\n"
        "final_vif = compute_vif(df[kept_features])\n"
        "print(f'Dropped by VIF: {dropped_vif}')\n"
        "print(f'Kept: {kept_features}')\n"
        "print('\\nFinal VIF (all should be < 10):')\n"
        "print(final_vif.to_string(index=False))\n"
        "assert final_vif['VIF'].max() <= VIF_THRESHOLD",
        "cell-08",
    ))

    cells.append(md_cell("## 4. Pairwise Correlation Filter", "cell-09"))

    cells.append(code_cell(
        "def correlation_filter(df, features, threshold):\n"
        "    corr        = df[features].corr().abs()\n"
        "    target_corr = df[features + ['label']].corr()['label'].abs()\n"
        "    to_drop = set()\n"
        "    for i, f1 in enumerate(features):\n"
        "        for f2 in features[i+1:]:\n"
        "            r = corr.loc[f1, f2]\n"
        "            if r > threshold:\n"
        "                drop = f1 if target_corr[f1] < target_corr[f2] else f2\n"
        "                to_drop.add(drop)\n"
        "                print(f'  Drop \"{drop}\" (r({f1},{f2})={r:.3f})')\n"
        "    kept = [f for f in features if f not in to_drop]\n"
        "    return kept, list(to_drop)\n"
        "\n"
        "\n"
        "print(f'Pairwise correlation filter (threshold |r|={CORR_THRESHOLD})...')\n"
        "features_after_corr, dropped_corr = correlation_filter(df, kept_features, CORR_THRESHOLD)\n"
        "print(f'Dropped: {dropped_corr}')\n"
        "print(f'Kept   : {features_after_corr}')",
        "cell-10",
    ))

    cells.append(md_cell("## 5. One-Hot Encode `land_cover_class`", "cell-11"))

    cells.append(code_cell(
        "FINAL_CONTINUOUS = features_after_corr\n"
        "\n"
        "print('land_cover_class value counts:')\n"
        "print(df['land_cover_class'].value_counts().sort_index())\n"
        "\n"
        "encoder   = OneHotEncoder(sparse_output=False, handle_unknown='ignore', dtype=np.float32)\n"
        "lc_array  = encoder.fit_transform(df[['land_cover_class']])\n"
        "lc_cols   = [f'lc_{int(c)}' for c in encoder.categories_[0]]\n"
        "df_lc     = pd.DataFrame(lc_array, columns=lc_cols, index=df.index)\n"
        "\n"
        "print(f'\\nOHE columns ({len(lc_cols)}): {lc_cols}')",
        "cell-12",
    ))

    cells.append(md_cell("## 6. Spatial Block Train/Test Split", "cell-13"))

    cells.append(code_cell(
        "MODEL_FEATURES = FINAL_CONTINUOUS + lc_cols\n"
        "\n"
        "# Assemble model-ready dataframe (unscaled — scale after split)\n"
        "df_model = pd.concat([\n"
        "    df[['lat', 'lon', 'label', 'block_id']].reset_index(drop=True),\n"
        "    df[FINAL_CONTINUOUS].reset_index(drop=True),\n"
        "    df_lc.reset_index(drop=True),\n"
        "], axis=1)\n"
        "\n"
        "# GroupShuffleSplit: no spatial block appears in both train and test\n"
        "gss = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=RANDOM_STATE)\n"
        "groups = df_model['block_id'].values\n"
        "train_idx, test_idx = next(gss.split(df_model, df_model['label'], groups=groups))\n"
        "\n"
        "df_train = df_model.iloc[train_idx].copy().reset_index(drop=True)\n"
        "df_test  = df_model.iloc[test_idx].copy().reset_index(drop=True)\n"
        "\n"
        "# Verify no block overlap\n"
        "train_blocks = set(df_train['block_id'])\n"
        "test_blocks  = set(df_test['block_id'])\n"
        "overlap = train_blocks & test_blocks\n"
        "assert len(overlap) == 0, f'Block overlap found: {overlap}'\n"
        "\n"
        "print('=== SPATIAL BLOCK TRAIN/TEST SPLIT ===')\n"
        "print(f'  Train: {len(df_train):,}  blocks={len(train_blocks)}  '\n"
        "      f'fire_rate={df_train.label.mean():.4f}')\n"
        "print(f'  Test : {len(df_test):,}   blocks={len(test_blocks)}   '\n"
        "      f'fire_rate={df_test.label.mean():.4f}')\n"
        "print(f'  Block overlap: {len(overlap)} (expected 0)')\n"
        "\n"
        "# Spatial plot of the split\n"
        "fig, ax = plt.subplots(figsize=(9, 7))\n"
        "ax.scatter(df_train['lon'], df_train['lat'], s=0.3, alpha=0.3,\n"
        "           c='#3498db', label=f'Train ({len(df_train):,})')\n"
        "ax.scatter(df_test['lon'],  df_test['lat'],  s=0.3, alpha=0.5,\n"
        "           c='#e74c3c', label=f'Test ({len(df_test):,})')\n"
        "ax.set_title('Spatial Block Split (20 km) — Train vs Test', fontsize=12)\n"
        "ax.set_xlabel('Longitude')\n"
        "ax.set_ylabel('Latitude')\n"
        "ax.legend(markerscale=8)\n"
        "ax.set_aspect('equal')\n"
        "plt.tight_layout()\n"
        "plt.savefig('../outputs/v2_spatial_block_split.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-14",
    ))

    cells.append(md_cell("## 7. StandardScaler (fit on train only)", "cell-15"))

    cells.append(code_cell(
        "# Fit scaler on train continuous features only\n"
        "scaler = StandardScaler()\n"
        "train_scaled = scaler.fit_transform(df_train[FINAL_CONTINUOUS])\n"
        "test_scaled  = scaler.transform(df_test[FINAL_CONTINUOUS])\n"
        "\n"
        "# Replace continuous features with scaled values\n"
        "df_train[FINAL_CONTINUOUS] = train_scaled\n"
        "df_test[FINAL_CONTINUOUS]  = test_scaled\n"
        "\n"
        "print('StandardScaler fitted on train, applied to test.')\n"
        "print(f'Train mean (should be ~0): {df_train[FINAL_CONTINUOUS].mean().round(4).values}')\n"
        "print(f'Train std  (should be ~1): {df_train[FINAL_CONTINUOUS].std().round(4).values}')",
        "cell-16",
    ))

    cells.append(md_cell("## 8. Save Outputs", "cell-17"))

    cells.append(code_cell(
        "# train_v2.csv and test_v2.csv include block_id for GroupKFold in modeling\n"
        "df_train.to_csv(PROCESSED / 'train_v2.csv', index=False)\n"
        "df_test.to_csv(PROCESSED  / 'test_v2.csv',  index=False)\n"
        "print(f'Saved train_v2.csv ({df_train.shape})  test_v2.csv ({df_test.shape})')\n"
        "\n"
        "with open(PROCESSED / 'scaler_v2.pkl', 'wb') as f:\n"
        "    pickle.dump(scaler, f)\n"
        "print('Saved scaler_v2.pkl')\n"
        "\n"
        "with open(PROCESSED / 'encoder_v2.pkl', 'wb') as f:\n"
        "    pickle.dump(encoder, f)\n"
        "print('Saved encoder_v2.pkl')\n"
        "\n"
        "feature_meta_v2 = {\n"
        "    'continuous_features'   : FINAL_CONTINUOUS,\n"
        "    'landcover_ohe_features': lc_cols,\n"
        "    'all_model_features'    : MODEL_FEATURES,\n"
        "    'dropped_vif'           : dropped_vif,\n"
        "    'dropped_correlation'   : dropped_corr,\n"
        "    'vif_threshold'         : VIF_THRESHOLD,\n"
        "    'corr_threshold'        : CORR_THRESHOLD,\n"
        "    'block_size_km'         : BLOCK_SIZE_M / 1000,\n"
        "    'pop_density_impute_median': float(pop_median),\n"
        "}\n"
        "with open(PROCESSED / 'selected_features_v2.json', 'w') as f:\n"
        "    json.dump(feature_meta_v2, f, indent=2)\n"
        "print('Saved selected_features_v2.json')",
        "cell-18",
    ))

    cells.append(md_cell("## 9. Verification", "cell-19"))

    cells.append(code_cell(
        "print('=== PREPROCESSING V2 VERIFICATION ===')\n"
        "\n"
        "# No NaN\n"
        "assert df_train.isnull().sum().sum() == 0\n"
        "assert df_test.isnull().sum().sum()  == 0\n"
        "print('  [OK] No NaN in train_v2 / test_v2')\n"
        "\n"
        "# VIF\n"
        "assert final_vif['VIF'].max() <= VIF_THRESHOLD\n"
        "print(f'  [OK] Max VIF = {final_vif[\"VIF\"].max():.2f} <= {VIF_THRESHOLD}')\n"
        "\n"
        "# Pairwise correlation\n"
        "corr_arr = df[FINAL_CONTINUOUS].corr().abs().to_numpy().copy()\n"
        "np.fill_diagonal(corr_arr, 0)\n"
        "max_corr = corr_arr.max()\n"
        "assert max_corr <= CORR_THRESHOLD\n"
        "print(f'  [OK] Max pairwise |r| = {max_corr:.3f} <= {CORR_THRESHOLD}')\n"
        "\n"
        "# No block overlap\n"
        "assert len(set(df_train['block_id']) & set(df_test['block_id'])) == 0\n"
        "print(f'  [OK] No spatial block overlap between train and test')\n"
        "\n"
        "# Files exist\n"
        "for fname in ['train_v2.csv', 'test_v2.csv', 'scaler_v2.pkl',\n"
        "              'encoder_v2.pkl', 'selected_features_v2.json']:\n"
        "    assert (PROCESSED / fname).exists()\n"
        "print('  [OK] All output files saved')\n"
        "\n"
        "print(f'\\nFinal features ({len(MODEL_FEATURES)}): {MODEL_FEATURES}')",
        "cell-20",
    ))

    return notebook(cells)


# ===========================================================================
# 04_modeling_v2.ipynb
# ===========================================================================

def make_04v2():
    cells = []

    cells.append(md_cell(
        "# 04 — Modeling v2 (Spatial Cross-Validation)\n\n"
        "Inputs: `train_v2.csv`, `test_v2.csv`, `selected_features_v2.json`\n\n"
        "Changes vs v1:\n"
        "- **`GroupKFold(n_splits=5)`** using spatial block IDs (vs `StratifiedKFold(n_splits=10)`)\n"
        "- Holdout test = spatially separate blocks (no leakage)\n"
        "- Expected AUC: 0.75 – 0.90 (proper spatial CV, vs ~0.997 with geographic confounding)\n\n"
        "Final cell shows **v1 vs v2 AUC comparison** to document the confounding effect.",
        "cell-00",
    ))

    cells.append(code_cell(
        "import warnings\n"
        "warnings.filterwarnings('ignore')\n"
        "\n"
        "import json\n"
        "import pickle\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "import seaborn as sns\n"
        "from pathlib import Path\n"
        "\n"
        "from sklearn.ensemble import RandomForestClassifier\n"
        "from sklearn.model_selection import GroupKFold, cross_validate\n"
        "from sklearn.metrics import (\n"
        "    roc_auc_score, accuracy_score, precision_score,\n"
        "    recall_score, f1_score, roc_curve, confusion_matrix,\n"
        "    ConfusionMatrixDisplay\n"
        ")\n"
        "from xgboost import XGBClassifier\n"
        "from lightgbm import LGBMClassifier\n"
        "import mlflow\n"
        "import mlflow.sklearn\n"
        "\n"
        "sns.set_theme(style='whitegrid', font_scale=1.1)\n"
        "\n"
        "PROCESSED  = Path('../data/processed')\n"
        "OUTPUTS    = Path('../outputs')\n"
        "MODELS_DIR = Path('../models')\n"
        "MLRUNS_DIR = Path('../mlruns')\n"
        "OUTPUTS.mkdir(exist_ok=True)\n"
        "MODELS_DIR.mkdir(exist_ok=True)\n"
        "\n"
        "RANDOM_STATE = 42\n"
        "CV_FOLDS     = 5\n"
        "EXPERIMENT   = 'wildfires-cordoba'\n"
        "\n"
        "print('All imports OK')",
        "cell-01",
    ))

    cells.append(md_cell("## 1. Load Data", "cell-02"))

    cells.append(code_cell(
        "with open(PROCESSED / 'selected_features_v2.json') as f:\n"
        "    feature_meta = json.load(f)\n"
        "\n"
        "MODEL_FEATURES = feature_meta['all_model_features']\n"
        "\n"
        "train = pd.read_csv(PROCESSED / 'train_v2.csv')\n"
        "test  = pd.read_csv(PROCESSED / 'test_v2.csv')\n"
        "\n"
        "X_train       = train[MODEL_FEATURES].values\n"
        "y_train       = train['label'].values\n"
        "block_ids_train = train['block_id'].values  # for GroupKFold\n"
        "\n"
        "X_test  = test[MODEL_FEATURES].values\n"
        "y_test  = test['label'].values\n"
        "\n"
        "print(f'Train: {X_train.shape}  fire_rate={y_train.mean():.4f}  blocks={train[\"block_id\"].nunique()}')\n"
        "print(f'Test : {X_test.shape}   fire_rate={y_test.mean():.4f}   blocks={test[\"block_id\"].nunique()}')\n"
        "print(f'Features ({len(MODEL_FEATURES)}): {MODEL_FEATURES}')",
        "cell-03",
    ))

    cells.append(md_cell("## 2. MLflow Setup", "cell-04"))

    cells.append(code_cell(
        "mlflow.set_tracking_uri(f'file://{MLRUNS_DIR.resolve()}')\n"
        "mlflow.set_experiment(EXPERIMENT)\n"
        "\n"
        "exp = mlflow.get_experiment_by_name(EXPERIMENT)\n"
        "print(f'Experiment: {EXPERIMENT}  (ID: {exp.experiment_id})')",
        "cell-05",
    ))

    cells.append(md_cell("## 3. Evaluation Helpers", "cell-06"))

    cells.append(code_cell(
        "GKF = GroupKFold(n_splits=CV_FOLDS)\n"
        "\n"
        "SCORING = {\n"
        "    'roc_auc'  : 'roc_auc',\n"
        "    'accuracy' : 'accuracy',\n"
        "    'precision': 'precision',\n"
        "    'recall'   : 'recall',\n"
        "    'f1'       : 'f1',\n"
        "}\n"
        "\n"
        "\n"
        "def evaluate_on_test(model, X_test, y_test):\n"
        "    y_prob = model.predict_proba(X_test)[:, 1]\n"
        "    y_pred = model.predict(X_test)\n"
        "    return {\n"
        "        'test_roc_auc'  : roc_auc_score(y_test, y_prob),\n"
        "        'test_accuracy' : accuracy_score(y_test, y_pred),\n"
        "        'test_precision': precision_score(y_test, y_pred, zero_division=0),\n"
        "        'test_recall'   : recall_score(y_test, y_pred, zero_division=0),\n"
        "        'test_f1'       : f1_score(y_test, y_pred, zero_division=0),\n"
        "    }\n"
        "\n"
        "\n"
        "def train_and_log_v2(name, model):\n"
        "    \"\"\"GroupKFold CV + holdout eval + MLflow logging.\"\"\"\n"
        "    print(f'Training {name}...', end=' ', flush=True)\n"
        "\n"
        "    cv_results = cross_validate(\n"
        "        model, X_train, y_train,\n"
        "        cv=GKF,\n"
        "        groups=block_ids_train,\n"
        "        scoring=SCORING,\n"
        "        return_train_score=False,\n"
        "        n_jobs=-1,\n"
        "    )\n"
        "\n"
        "    model.fit(X_train, y_train)\n"
        "    holdout     = evaluate_on_test(model, X_test, y_test)\n"
        "    cv_auc_mean = cv_results['test_roc_auc'].mean()\n"
        "    cv_auc_std  = cv_results['test_roc_auc'].std()\n"
        "    print(f'CV AUC={cv_auc_mean:.4f} ± {cv_auc_std:.4f}  |  Test AUC={holdout[\"test_roc_auc\"]:.4f}')\n"
        "\n"
        "    with mlflow.start_run(run_name=f'{name}_v2_baseline') as run:\n"
        "        mlflow.set_tag('phase',   'v2_baseline')\n"
        "        mlflow.set_tag('model',   name)\n"
        "        mlflow.set_tag('cv_type', 'GroupKFold_spatial')\n"
        "        for k, v in model.get_params().items():\n"
        "            mlflow.log_param(k, v)\n"
        "        for metric in SCORING:\n"
        "            mlflow.log_metric(f'cv_{metric}_mean', cv_results[f'test_{metric}'].mean())\n"
        "            mlflow.log_metric(f'cv_{metric}_std',  cv_results[f'test_{metric}'].std())\n"
        "        for k, v in holdout.items():\n"
        "            mlflow.log_metric(k, v)\n"
        "        mlflow.sklearn.log_model(model, artifact_path='model')\n"
        "        run_id = run.info.run_id\n"
        "\n"
        "    return {\n"
        "        'name'        : name,\n"
        "        'model'       : model,\n"
        "        'run_id'      : run_id,\n"
        "        'cv_auc_mean' : cv_auc_mean,\n"
        "        'cv_auc_std'  : cv_auc_std,\n"
        "        'cv_acc_mean' : cv_results['test_accuracy'].mean(),\n"
        "        'cv_prec_mean': cv_results['test_precision'].mean(),\n"
        "        'cv_rec_mean' : cv_results['test_recall'].mean(),\n"
        "        'cv_f1_mean'  : cv_results['test_f1'].mean(),\n"
        "        **holdout,\n"
        "    }\n"
        "\n"
        "print('Helper functions defined.')",
        "cell-07",
    ))

    cells.append(md_cell(
        "## 4. Baseline Models (Spatial GroupKFold CV)\n\n"
        "Default hyperparameters — no tuning. Goal: AUC in 0.75–0.90 range with proper spatial CV.",
        "cell-08",
    ))

    cells.append(code_cell(
        "rf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=RANDOM_STATE)\n"
        "result_rf = train_and_log_v2('RandomForest', rf)",
        "cell-09",
    ))

    cells.append(code_cell(
        "xgb = XGBClassifier(\n"
        "    n_estimators=200, learning_rate=0.1, max_depth=6,\n"
        "    subsample=0.8, colsample_bytree=0.8,\n"
        "    eval_metric='logloss', n_jobs=-1, random_state=RANDOM_STATE\n"
        ")\n"
        "result_xgb = train_and_log_v2('XGBoost', xgb)",
        "cell-10",
    ))

    cells.append(code_cell(
        "lgbm = LGBMClassifier(\n"
        "    n_estimators=200, learning_rate=0.1, num_leaves=63,\n"
        "    subsample=0.8, colsample_bytree=0.8,\n"
        "    n_jobs=-1, random_state=RANDOM_STATE, verbose=-1\n"
        ")\n"
        "result_lgbm = train_and_log_v2('LightGBM', lgbm)",
        "cell-11",
    ))

    cells.append(md_cell("## 5. Comparison Table & Plots", "cell-12"))

    cells.append(code_cell(
        "results_v2 = [result_rf, result_xgb, result_lgbm]\n"
        "\n"
        "metrics_df = pd.DataFrame([{\n"
        "    'Model'   : r['name'],\n"
        "    'CV AUC'  : f\"{r['cv_auc_mean']:.4f} ± {r['cv_auc_std']:.4f}\",\n"
        "    'CV Acc'  : f\"{r['cv_acc_mean']:.4f}\",\n"
        "    'CV F1'   : f\"{r['cv_f1_mean']:.4f}\",\n"
        "    'Test AUC': f\"{r['test_roc_auc']:.4f}\",\n"
        "    'Test Acc': f\"{r['test_accuracy']:.4f}\",\n"
        "    'Test F1' : f\"{r['test_f1']:.4f}\",\n"
        "} for r in results_v2])\n"
        "metrics_df.set_index('Model', inplace=True)\n"
        "print('=== V2 SPATIAL CV BASELINE ===')\n"
        "print(metrics_df.to_string())\n"
        "metrics_df",
        "cell-13",
    ))

    cells.append(code_cell(
        "# ROC curves\n"
        "fig, ax = plt.subplots(figsize=(8, 6))\n"
        "colors = ['#2980b9', '#e67e22', '#27ae60']\n"
        "for r, color in zip(results_v2, colors):\n"
        "    y_prob    = r['model'].predict_proba(X_test)[:, 1]\n"
        "    fpr, tpr, _ = roc_curve(y_test, y_prob)\n"
        "    ax.plot(fpr, tpr, color=color, linewidth=2,\n"
        "            label=f\"{r['name']} (AUC={r['test_roc_auc']:.4f})\")\n"
        "\n"
        "ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random')\n"
        "ax.set_xlabel('False Positive Rate', fontsize=12)\n"
        "ax.set_ylabel('True Positive Rate', fontsize=12)\n"
        "ax.set_title('ROC Curves — v2 Baselines (Spatial CV, Holdout Test)', fontsize=12)\n"
        "ax.legend(fontsize=11)\n"
        "ax.grid(True, alpha=0.3)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_roc_curves.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-14",
    ))

    cells.append(code_cell(
        "# Confusion matrices\n"
        "fig, axes = plt.subplots(1, 3, figsize=(15, 4))\n"
        "for r, ax in zip(results_v2, axes):\n"
        "    y_pred = r['model'].predict(X_test)\n"
        "    cm = confusion_matrix(y_test, y_pred)\n"
        "    disp = ConfusionMatrixDisplay(cm, display_labels=['No-fire', 'Fire'])\n"
        "    disp.plot(ax=ax, colorbar=False, cmap='Blues')\n"
        "    ax.set_title(f\"{r['name']}\\nAUC={r['test_roc_auc']:.4f}  F1={r['test_f1']:.4f}\",\n"
        "                 fontsize=11)\n"
        "plt.suptitle('Confusion Matrices — v2 Baselines (Spatial CV)', fontsize=13)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_confusion_matrices.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-15",
    ))

    cells.append(code_cell(
        "# Feature importances\n"
        "fig, axes = plt.subplots(1, 3, figsize=(16, 6))\n"
        "for r, ax in zip(results_v2, axes):\n"
        "    model = r['model']\n"
        "    imp   = model.feature_importances_ if hasattr(model, 'feature_importances_') \\\n"
        "            else np.zeros(len(MODEL_FEATURES))\n"
        "    imp_df = pd.Series(imp, index=MODEL_FEATURES).sort_values(ascending=True).tail(15)\n"
        "    imp_df.plot(kind='barh', ax=ax, color='#27ae60')\n"
        "    ax.set_title(f\"{r['name']} — Feature Importance\", fontsize=11)\n"
        "    ax.set_xlabel('Importance')\n"
        "plt.suptitle('Native Feature Importances (top-15) — v2 Spatial CV', fontsize=13)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v2_feature_importance.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-16",
    ))

    cells.append(md_cell(
        "## 6. v1 vs v2 AUC Comparison\n\n"
        "This table is the key evidence of geographic confounding.\n"
        "The AUC drop from v1 (random CV, biased sampling) to v2 (spatial CV, elevation-stratified)\n"
        "quantifies how much of the v1 performance was spurious.",
        "cell-17",
    ))

    cells.append(code_cell(
        "# Load v1 metrics\n"
        "with open(OUTPUTS / 'baseline_metrics.json') as f:\n"
        "    v1_metrics = json.load(f)\n"
        "v1_df = pd.DataFrame(v1_metrics)[['model', 'cv_auc_mean', 'test_roc_auc']]\n"
        "v1_df.columns = ['Model', 'v1_CV_AUC', 'v1_Test_AUC']\n"
        "\n"
        "# Build v2 metrics\n"
        "v2_df = pd.DataFrame([{\n"
        "    'Model'       : r['name'],\n"
        "    'v2_CV_AUC'   : r['cv_auc_mean'],\n"
        "    'v2_Test_AUC' : r['test_roc_auc'],\n"
        "} for r in results_v2])\n"
        "\n"
        "comparison = v1_df.merge(v2_df, on='Model')\n"
        "comparison['CV_AUC_drop']   = comparison['v1_CV_AUC']   - comparison['v2_CV_AUC']\n"
        "comparison['Test_AUC_drop'] = comparison['v1_Test_AUC'] - comparison['v2_Test_AUC']\n"
        "comparison.set_index('Model', inplace=True)\n"
        "\n"
        "print('=== v1 vs v2 AUC COMPARISON ===')\n"
        "print('v1 = random StratifiedKFold(10) + 5km buffer (geographically confounded)')\n"
        "print('v2 = spatial GroupKFold(5) + 1km buffer + elevation stratification')\n"
        "print()\n"
        "print(comparison.round(4).to_string())",
        "cell-18",
    ))

    cells.append(code_cell(
        "# Bar chart: AUC comparison\n"
        "fig, axes = plt.subplots(1, 2, figsize=(13, 5))\n"
        "\n"
        "models = comparison.index.tolist()\n"
        "x = np.arange(len(models))\n"
        "width = 0.35\n"
        "\n"
        "for ax, v1_col, v2_col, title in [\n"
        "    (axes[0], 'v1_CV_AUC',   'v2_CV_AUC',   'Cross-Validation AUC'),\n"
        "    (axes[1], 'v1_Test_AUC', 'v2_Test_AUC', 'Holdout Test AUC'),\n"
        "]:\n"
        "    bars1 = ax.bar(x - width/2, comparison[v1_col], width, label='v1 (random CV, confounded)',\n"
        "                   color='#e74c3c', alpha=0.8)\n"
        "    bars2 = ax.bar(x + width/2, comparison[v2_col], width, label='v2 (spatial CV, fixed)',\n"
        "                   color='#27ae60', alpha=0.8)\n"
        "    ax.set_xticks(x)\n"
        "    ax.set_xticklabels(models)\n"
        "    ax.set_ylim(0, 1.05)\n"
        "    ax.axhline(0.9, ls='--', color='gray', alpha=0.5, lw=1, label='AUC=0.90')\n"
        "    ax.set_ylabel('AUC-ROC')\n"
        "    ax.set_title(title, fontsize=12)\n"
        "    ax.legend(fontsize=9)\n"
        "    ax.grid(axis='y', alpha=0.3)\n"
        "    # Annotate bars\n"
        "    for bar in [*bars1, *bars2]:\n"
        "        h = bar.get_height()\n"
        "        ax.text(bar.get_x() + bar.get_width()/2, h + 0.005,\n"
        "                f'{h:.3f}', ha='center', va='bottom', fontsize=8)\n"
        "\n"
        "plt.suptitle('Geographic Confounding: v1 vs v2 AUC\\n'\n"
        "             '(AUC drop = spurious performance from biased negative sampling)', fontsize=12)\n"
        "plt.tight_layout()\n"
        "plt.savefig(OUTPUTS / 'v1_vs_v2_auc_comparison.png', dpi=150, bbox_inches='tight')\n"
        "plt.show()",
        "cell-19",
    ))

    cells.append(md_cell("## 7. Save v2 Results", "cell-20"))

    cells.append(code_cell(
        "# Save per-model files\n"
        "for r in results_v2:\n"
        "    p = MODELS_DIR / f'{r[\"name\"].lower()}_v2_baseline.pkl'\n"
        "    with open(p, 'wb') as f:\n"
        "        pickle.dump(r['model'], f)\n"
        "    print(f'Saved: {p}')\n"
        "\n"
        "# Save metrics\n"
        "v2_summary = [{\n"
        "    'model'         : r['name'],\n"
        "    'cv_auc_mean'   : r['cv_auc_mean'],\n"
        "    'cv_auc_std'    : r['cv_auc_std'],\n"
        "    'test_roc_auc'  : r['test_roc_auc'],\n"
        "    'test_accuracy' : r['test_accuracy'],\n"
        "    'test_precision': r['test_precision'],\n"
        "    'test_recall'   : r['test_recall'],\n"
        "    'test_f1'       : r['test_f1'],\n"
        "    'run_id'        : r['run_id'],\n"
        "} for r in results_v2]\n"
        "\n"
        "with open(OUTPUTS / 'v2_baseline_metrics.json', 'w') as f:\n"
        "    json.dump(v2_summary, f, indent=2)\n"
        "print('Saved: outputs/v2_baseline_metrics.json')",
        "cell-21",
    ))

    cells.append(md_cell("## 8. Verification", "cell-22"))

    cells.append(code_cell(
        "print('=== MODELING V2 VERIFICATION ===')\n"
        "\n"
        "# AUC floor (below 0.65 = over-corrected)\n"
        "for r in results_v2:\n"
        "    assert r['test_roc_auc'] > 0.65, f'{r[\"name\"]} AUC too low: {r[\"test_roc_auc\"]:.4f}'\n"
        "    flag = ' < SUSPICIOUS (check over-correction)' if r['test_roc_auc'] > 0.97 else ''\n"
        "    print(f'  [OK] {r[\"name\"]} test AUC = {r[\"test_roc_auc\"]:.4f} > 0.65{flag}')\n"
        "\n"
        "# AUC drop vs v1\n"
        "print()\n"
        "for _, row in comparison.iterrows():\n"
        "    drop = row['Test_AUC_drop']\n"
        "    symbol = 'OK' if drop > 0.02 else 'WARN'\n"
        "    print(f'  [{symbol}] {row.name}: Test AUC drop = {drop:.4f} '\n"
        "          f'(v1={row[\"v1_Test_AUC\"]:.4f} → v2={row[\"v2_Test_AUC\"]:.4f})')\n"
        "\n"
        "# No block leakage\n"
        "train_b = set(train['block_id'])\n"
        "test_b  = set(test['block_id'])\n"
        "assert len(train_b & test_b) == 0\n"
        "print(f'\\n  [OK] No spatial block overlap (train={len(train_b)}, test={len(test_b)} blocks)')\n"
        "\n"
        "# Files saved\n"
        "assert (OUTPUTS / 'v2_baseline_metrics.json').exists()\n"
        "print('  [OK] v2_baseline_metrics.json saved')\n"
        "\n"
        "best_v2 = max(results_v2, key=lambda r: r['test_roc_auc'])\n"
        "print(f'\\nBest v2 model: {best_v2[\"name\"]} (Test AUC={best_v2[\"test_roc_auc\"]:.4f})')",
        "cell-23",
    ))

    return notebook(cells)


# ===========================================================================
# Write notebooks
# ===========================================================================

if __name__ == "__main__":
    save(make_03a(), NB_DIR / "03a_resampling.ipynb")
    save(make_03b(), NB_DIR / "03b_preprocessing_v2.ipynb")
    save(make_04v2(), NB_DIR / "04_modeling_v2.ipynb")
    print("\nAll notebooks created successfully.")
