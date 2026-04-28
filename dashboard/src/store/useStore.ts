'use client';

import { create } from 'zustand';

export type ViewId = 'risk-extrusion' | 'hexbin' | 'flyover' | 'analysis';
export type BasemapStyle = 'terrain' | 'satellite' | 'streets';

export interface PopupData {
  lon: number;
  lat: number;
  prob: number;
  cls: number;
  shapValues: Record<string, number> | null;
}

export interface LayerToggles {
  showFires: boolean;
  showZones: boolean;
  showHeatmap: boolean;
}

interface AppState {
  activeView: ViewId;
  setActiveView: (v: ViewId) => void;

  basemap: BasemapStyle;
  setBasemap: (b: BasemapStyle) => void;

  layers: LayerToggles;
  toggleLayer: (key: keyof LayerToggles) => void;

  hexRadius: number;
  setHexRadius: (r: number) => void;

  riskOpacity: number;
  setRiskOpacity: (o: number) => void;

  yearRange: [number, number];
  setYearRange: (r: [number, number]) => void;

  popup: PopupData | null;
  setPopup: (p: PopupData | null) => void;

  // Grid data (typed arrays, loaded once)
  gridLoaded: boolean;
  gridLons: Float32Array | null;
  gridLats: Float32Array | null;
  gridProbs: Float32Array | null;
  gridClasses: Uint8Array | null;
  setGridData: (
    lons: Float32Array,
    lats: Float32Array,
    probs: Float32Array,
    classes: Uint8Array,
  ) => void;

  // Fire data (typed arrays, loaded once)
  firesLoaded: boolean;
  fireLons: Float32Array | null;
  fireLats: Float32Array | null;
  fireYearOffsets: Uint8Array | null;
  fireMonths: Uint8Array | null;
  nModisFires: number;
  setFireData: (
    lons: Float32Array,
    lats: Float32Array,
    yearOffsets: Uint8Array,
    months: Uint8Array,
    nModis: number,
  ) => void;

  // SHAP samples
  shapSamples: Record<string, number>[] | null;
  setShapSamples: (s: Record<string, number>[]) => void;
}

export const useStore = create<AppState>((set) => ({
  activeView: 'risk-extrusion',
  setActiveView: (activeView) => set({ activeView }),

  basemap: 'terrain',
  setBasemap: (basemap) => set({ basemap }),

  layers: {
    showFires: false,
    showZones: false,
    showHeatmap: true,
  },
  toggleLayer: (key) =>
    set((s) => ({ layers: { ...s.layers, [key]: !s.layers[key] } })),

  hexRadius: 8000,
  setHexRadius: (hexRadius) => set({ hexRadius }),

  riskOpacity: 1.0,
  setRiskOpacity: (riskOpacity) => set({ riskOpacity }),

  yearRange: [2001, 2024],
  setYearRange: (yearRange) => set({ yearRange }),

  popup: null,
  setPopup: (popup) => set({ popup }),

  gridLoaded: false,
  gridLons: null,
  gridLats: null,
  gridProbs: null,
  gridClasses: null,
  setGridData: (lons, lats, probs, classes) =>
    set({ gridLons: lons, gridLats: lats, gridProbs: probs, gridClasses: classes, gridLoaded: true }),

  firesLoaded: false,
  fireLons: null,
  fireLats: null,
  fireYearOffsets: null,
  fireMonths: null,
  nModisFires: 0,
  setFireData: (lons, lats, yearOffsets, months, nModis) =>
    set({
      fireLons: lons,
      fireLats: lats,
      fireYearOffsets: yearOffsets,
      fireMonths: months,
      nModisFires: nModis,
      firesLoaded: true,
    }),

  shapSamples: null,
  setShapSamples: (shapSamples) => set({ shapSamples }),
}));
