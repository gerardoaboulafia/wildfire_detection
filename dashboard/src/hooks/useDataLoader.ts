'use client';

import { useEffect, useRef } from 'react';
import { loadGrid, loadGridMeta, loadFires, loadFiresMeta } from '@/lib/loadBinary';
import { useStore } from '@/store/useStore';

/**
 * Loads all binary data on mount. Runs once.
 * Sets gridLoaded and firesLoaded in the Zustand store when done.
 */
export function useDataLoader() {
  const loaded = useRef(false);
  const setGridData = useStore((s) => s.setGridData);
  const setFireData = useStore((s) => s.setFireData);
  const setShapSamples = useStore((s) => s.setShapSamples);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;

    async function load() {
      // Load grid and fires in parallel
      const [gridMeta, firesMeta] = await Promise.all([
        loadGridMeta(),
        loadFiresMeta(),
      ]);

      const [grid, fires, shapRes] = await Promise.all([
        loadGrid(gridMeta),
        loadFires(firesMeta),
        fetch('/data/shap_samples.json').then((r) => r.json()),
      ]);

      setGridData(grid.lons, grid.lats, grid.probs, grid.classes);
      setFireData(fires.lons, fires.lats, fires.yearOffsets, fires.months, fires.nModis);
      setShapSamples(shapRes);
    }

    load().catch(console.error);
  }, [setGridData, setFireData, setShapSamples]);
}
