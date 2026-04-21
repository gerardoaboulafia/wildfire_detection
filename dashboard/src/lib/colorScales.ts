// Risk zone colors: Low (green) → Moderate (yellow) → High (orange) → Very High (red)
// Format: [R, G, B, A] (0–255)
export const RISK_COLORS: Record<number, [number, number, number, number]> = {
  1: [34, 197, 94, 200],   // green-500
  2: [234, 179, 8, 200],   // yellow-500
  3: [249, 115, 22, 200],  // orange-500
  4: [220, 38, 38, 220],   // red-600
};

// Fill colors for GeoJSON zone layer — semi-transparent so basemap roads/labels show through
export const ZONE_FILL_COLORS: Record<string, [number, number, number, number]> = {
  Low: [34, 197, 94, 140],
  Moderate: [234, 179, 8, 140],
  High: [249, 115, 22, 160],
  'Very High': [220, 38, 38, 180],
};

// Hex aggregation color range (sequential: light yellow → dark red)
export const HEX_COLOR_RANGE: [number, number, number][] = [
  [254, 240, 217],
  [253, 212, 158],
  [253, 187, 132],
  [252, 141, 89],
  [227, 74, 51],
  [179, 0, 0],
];

// Heatmap color range
export const HEATMAP_COLOR_RANGE: [number, number, number, number][] = [
  [0, 128, 0, 0],
  [34, 197, 94, 100],
  [234, 179, 8, 180],
  [249, 115, 22, 220],
  [220, 38, 38, 255],
];
