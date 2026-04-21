// Córdoba Province bounding box and default viewport
export const CORDOBA_BBOX = {
  lonMin: -65.7783,
  lonMax: -61.7777,
  latMin: -34.9987,
  latMax: -29.5033,
};

export const INITIAL_VIEW_STATE = {
  longitude: -63.78,
  latitude: -32.25,
  zoom: 6.5,
  pitch: 0,
  bearing: 0,
};

export const MAPBOX_STYLES = {
  terrain: 'mapbox://styles/mapbox/outdoors-v12',
  satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
  streets: 'mapbox://styles/mapbox/light-v11',
} as const;

export const CLASS_LABELS: Record<number, string> = {
  1: 'Low',
  2: 'Moderate',
  3: 'High',
  4: 'Very High',
};

export const SHAP_FEATURE_LABELS: Record<string, string> = {
  clay: 'Clay Content (%)',
  distance_to_settlement_km: 'Distance to Settlement (km)',
  elevation: 'Elevation (m)',
  population_density: 'Population Density',
  distance_to_river_km: 'Distance to River (km)',
  slope: 'Slope (°)',
  distance_to_road_km: 'Distance to Road (km)',
  lc_40: 'Land Cover: Herbaceous',
  lc_20: 'Land Cover: Shrubs',
  aspect_cos: 'Aspect (cos)',
  lc_30: 'Land Cover: Herbaceous+Shrubs',
  lc_50: 'Land Cover: Urban',
  lc_116: 'Land Cover: Closed Forest',
  lc_90: 'Land Cover: Herbaceous Wetland',
  lc_126: 'Land Cover: Mangroves',
  lc_114: 'Land Cover: Open Forest',
  lc_60: 'Land Cover: Bare/Sparse',
  lc_80: 'Land Cover: Permanent Water',
  lc_124: 'Land Cover: Flooded Forest',
};
