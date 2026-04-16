export interface GridMeta {
  n_points: number;
  lon_min: number;
  lon_max: number;
  lat_min: number;
  lat_max: number;
  class_labels: Record<string, string>;
  class_thresholds: Record<string, { min: number; max: number }>;
  area_km2: Record<string, number>;
  cell_area_km2: number;
}

export interface FiresMeta {
  n_modis: number;
  n_viirs: number;
  n_total: number;
  bytes_per_record: number;
}

export interface GridArrays {
  lons: Float32Array;
  lats: Float32Array;
  probs: Float32Array;
  classes: Uint8Array;
}

export interface FireArrays {
  lons: Float32Array;
  lats: Float32Array;
  yearOffsets: Uint8Array;
  months: Uint8Array;
  nModis: number;
}

export async function loadGridMeta(): Promise<GridMeta> {
  const res = await fetch('/data/grid_meta.json');
  return res.json();
}

export async function loadFiresMeta(): Promise<FiresMeta> {
  const res = await fetch('/data/fires_meta.json');
  return res.json();
}

/**
 * Decode grid.bin: [u16 lon_off][u16 lat_off][u16 prob][u8 class] = 7 bytes/point
 */
export async function loadGrid(meta: GridMeta): Promise<GridArrays> {
  const res = await fetch('/data/grid.bin');
  const buf = await res.arrayBuffer();
  const n = meta.n_points;
  const view = new DataView(buf);

  const lons = new Float32Array(n);
  const lats = new Float32Array(n);
  const probs = new Float32Array(n);
  const classes = new Uint8Array(n);

  const lonRange = meta.lon_max - meta.lon_min;
  const latRange = meta.lat_max - meta.lat_min;

  for (let i = 0; i < n; i++) {
    const offset = i * 7;
    lons[i] = meta.lon_min + (view.getUint16(offset, true) / 65535) * lonRange;
    lats[i] = meta.lat_min + (view.getUint16(offset + 2, true) / 65535) * latRange;
    probs[i] = view.getUint16(offset + 4, true) / 65535;
    classes[i] = view.getUint8(offset + 6);
  }

  return { lons, lats, probs, classes };
}

/**
 * Decode fires.bin: [f32 lon][f32 lat][u8 year_off][u8 month] = 10 bytes/point
 */
export async function loadFires(meta: FiresMeta): Promise<FireArrays> {
  const res = await fetch('/data/fires.bin');
  const buf = await res.arrayBuffer();
  const n = meta.n_total;
  const view = new DataView(buf);

  const lons = new Float32Array(n);
  const lats = new Float32Array(n);
  const yearOffsets = new Uint8Array(n);
  const months = new Uint8Array(n);

  for (let i = 0; i < n; i++) {
    const offset = i * 10;
    lons[i] = view.getFloat32(offset, true);
    lats[i] = view.getFloat32(offset + 4, true);
    yearOffsets[i] = view.getUint8(offset + 8);
    months[i] = view.getUint8(offset + 9);
  }

  return { lons, lats, yearOffsets, months, nModis: meta.n_modis };
}
