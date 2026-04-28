# NASA DEVELOP Project: Wildland Fire Analysis in Córdoba, Argentina

## Project Overview & Objectives

### Project Context
A NASA DEVELOP National Program project from Summer 2024 analyzing wildland fires in Córdoba, Argentina.

**Partner:** Instituto Nacional de Tecnología Agropecuaria (INTA)

### Core Objective
Assess the feasibility of using Earth Observations (EO) to identify environmental parameters influencing fire behavior, quantify temporal anomalies leading to the intense September 2020 fires, and generate a fire risk probability map to inform INTA's fire management strategies.

### Target Event & Study Period
- **Target Event:** September 2020 wildfires
- **Study Period:** Six months prior to the fires (March to August 2020) to capture the transition from the rainy to the dry/fire season
- **Baseline Period:** 2010 to 2019 (March to September) was used to establish normal climatic conditions and identify anomalies

---

## Data Sources & Variables

The study utilized multiple Earth Observation platforms to gather environmental data.

| Variable | Source | Resolution | Collection Interval |
|----------|--------|-----------|-------------------|
| **Burned Area** | Terra and Aqua MODIS (MCD64A1 V6.1 and FireCCI5 V5.1) | 500m & 250m | — |
| **NDVI** | Terra MODIS (MOD13Q1 V6.1) | 250m | 16-day |
| **Evapotranspiration (ET)** | Terra MODIS (MOD16A2 V6.1) | 500m | 8-day |
| **Land Surface Temperature (LST)** | Terra MODIS (MOD11A1 V6.1) | 1000m | Daily |
| **Precipitation** | GPM IMERG (GPM_3IMERGD V6) | ~11km | 30-minute |
| **Soil Moisture** | SMAP (SPL4SMGP.007) | 9km | 3-hour |
| **Topography** (Elevation & Slope) | SRTM (1 Arc-Second Global) | 30m | — |
| **Wildland-Urban Interface (WUI)** | University of Wisconsin-Madison (2020) | 10m | — |

**Note:** Soil moisture baseline was restricted to 2016-2019 due to data availability constraints.

---

## Data Processing & Transformations

### Platform Toolkit
- **Data Acquisition & Pixel Extraction:** Google Earth Engine (GEE) JavaScript API
- **Spatial Processing:** ArcGIS Pro (clipping and masking)
- **Statistical Analysis:** R Studio

### Site Selection
- **WUI Data:** Clipped to Córdoba, masking out water and urban areas to isolate wildland vegetation
- **Burned Sites:** Identified using September 2020 MODIS data
- **Unburned Control Sites:** Selected by excluding areas that had burned within the preceding two years (August 2018 to August 2020)

### Data Transformations

#### Precipitation
Half-hourly GPM data was summed to create daily precipitation values.

#### NDVI (Normalized Difference Vegetation Index)
Calculated using the formula:
$$NDVI = \frac{NIR - Red}{NIR + Red}$$

A scale factor of 0.0001 was applied.

#### Land Surface Temperature (LST)
- Scale factor of 0.02 was applied
- Values converted from Kelvin to Celsius

#### Evapotranspiration (ET)
- Scale factor of 0.1 was applied to represent values in kg/m² per 8 days

#### Anomalies
Calculated by subtracting the 2010-2019 monthly baseline means from the 2020 values.

---

## Modeling & Statistical Analysis

### 1. Logistic Regression

**Purpose:** Determine the statistical significance of environmental variables as precursors to fire occurrences.

#### Key Results

**Significant Negative Correlation:**
- NDVI
- Precipitation
- Soil Moisture
- LST

*Interpretation:* As these values decrease, fire likelihood increases.

**Significant Positive Correlation:**
- Elevation

*Interpretation:* Higher elevations showed increased fire likelihood.

**Not Significant:**
- Slope
- Evapotranspiration

#### Model Performance
| Metric | Value |
|--------|-------|
| Accuracy | 70.2% |
| Precision | 72.0% |
| Recall | 83.1% |
| F1-Score | 77.1% |
| Specificity | 50.4% |

**Interpretation:** The model is strong at identifying positive fire instances but struggles slightly with false positives.

### 2. Random Forest

**Purpose:** Evaluate the relative importance of each variable and map spatial fire risk probabilities.

#### Variable Importance Ranking
1. NDVI
2. Precipitation
3. Elevation
4. ET
5. Soil Moisture
6. LST
7. Slope

#### Partial Dependence Plots (PDPs) Thresholds

**NDVI**
- Fire probability peaks sharply when NDVI values are between 0.25 and 0.30
- Drops significantly as vegetation density/health increases

**Precipitation**
- Fire probability is highest at extremely low precipitation levels (10-15mm)
- Drops off non-linearly as rainfall increases

---

## Limitations & Uncertainties

### Resolution Mismatches
Relying on multiple sensors meant combining coarse spatial resolutions (like 9km GPM data) with higher resolutions, creating a pixelated final risk map.

### Data Gaps
Infrequent collection intervals and cloud cover shortened usable data periods.

### Missing Variables
The absence of a specific vegetation type map limited the team's ability to cross-reference areas with intrinsically higher fuel loads.