'use client';

import { useMemo } from 'react';
import { HexagonLayer } from '@deck.gl/aggregation-layers';
import { useStore } from '@/store/useStore';

interface FirePoint {
  position: [number, number];
}

// 6-step sequential color ramp: light yellow → dark red
const COLOR_RANGE: [number, number, number, number][] = [
  [254, 240, 217, 200],
  [253, 212, 158, 210],
  [253, 187, 132, 220],
  [252, 141, 89, 230],
  [227, 74, 51, 240],
  [179, 0, 0, 255],
];

export function useHexLayer(enabled: boolean) {
  const fireLons = useStore((s) => s.fireLons);
  const fireLats = useStore((s) => s.fireLats);
  const fireYearOffsets = useStore((s) => s.fireYearOffsets);
  const hexRadius = useStore((s) => s.hexRadius);
  const yearRange = useStore((s) => s.yearRange);

  const data = useMemo<FirePoint[]>(() => {
    if (!fireLons || !fireLats || !fireYearOffsets) return [];
    const [yMin, yMax] = yearRange;
    const n = fireLons.length;
    const arr: FirePoint[] = [];
    for (let i = 0; i < n; i++) {
      const year = 2000 + fireYearOffsets[i];
      if (year < yMin || year > yMax) continue;
      arr.push({ position: [fireLons[i], fireLats[i]] });
    }
    return arr;
  }, [fireLons, fireLats, fireYearOffsets, yearRange]);

  if (!enabled || data.length === 0) return null;

  return new HexagonLayer<FirePoint>({
    id: 'fire-hexbin',
    data,
    getPosition: (d) => d.position,
    radius: hexRadius,
    extruded: true,
    elevationScale: 100,
    colorRange: COLOR_RANGE,
    coverage: 0.88,
    pickable: true,
    gpuAggregation: false,   // CPU aggregation — required when not in interleaved mode
  });
}
