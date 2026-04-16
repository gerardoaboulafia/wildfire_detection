'use client';

import { useMemo } from 'react';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { useStore } from '@/store/useStore';

interface FirePoint {
  position: [number, number];
  weight: number;
}

export function useFireDensityLayer(enabled: boolean) {
  const fireLons = useStore((s) => s.fireLons);
  const fireLats = useStore((s) => s.fireLats);
  const fireYearOffsets = useStore((s) => s.fireYearOffsets);
  const yearRange = useStore((s) => s.yearRange);

  const data = useMemo<FirePoint[]>(() => {
    if (!fireLons || !fireLats || !fireYearOffsets) return [];
    const [yMin, yMax] = yearRange;
    const n = fireLons.length;
    const arr: FirePoint[] = [];
    for (let i = 0; i < n; i++) {
      const year = 2000 + fireYearOffsets[i];
      if (year < yMin || year > yMax) continue;
      arr.push({ position: [fireLons[i], fireLats[i]], weight: 1 });
    }
    return arr;
  }, [fireLons, fireLats, fireYearOffsets, yearRange]);

  if (!enabled || data.length === 0) return null;

  return new HeatmapLayer<FirePoint>({
    id: 'fire-density-heatmap',
    data,
    getPosition: (d) => d.position,
    getWeight: (d) => d.weight,
    radiusPixels: 30,
    intensity: 1.5,
    threshold: 0.03,
    colorRange: [
      [255, 255, 178],
      [254, 204, 92],
      [253, 141, 60],
      [240, 59, 32],
      [189, 0, 38],
    ],
  });
}
