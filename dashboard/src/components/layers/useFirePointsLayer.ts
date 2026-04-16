'use client';

import { useMemo } from 'react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { useStore } from '@/store/useStore';

interface FirePoint {
  position: [number, number];
  year: number;
  isViirs: boolean;
}

export function useFirePointsLayer(enabled: boolean) {
  const fireLons = useStore((s) => s.fireLons);
  const fireLats = useStore((s) => s.fireLats);
  const fireYearOffsets = useStore((s) => s.fireYearOffsets);
  const nModisFires = useStore((s) => s.nModisFires);
  const yearRange = useStore((s) => s.yearRange);

  const data = useMemo<FirePoint[]>(() => {
    if (!fireLons || !fireLats || !fireYearOffsets) return [];
    const n = fireLons.length;
    const arr: FirePoint[] = [];
    const [yMin, yMax] = yearRange;
    for (let i = 0; i < n; i++) {
      const year = 2000 + fireYearOffsets[i];
      if (year < yMin || year > yMax) continue;
      arr.push({
        position: [fireLons[i], fireLats[i]],
        year,
        isViirs: i >= nModisFires,
      });
    }
    return arr;
  }, [fireLons, fireLats, fireYearOffsets, nModisFires, yearRange]);

  if (!enabled || data.length === 0) return null;

  return new ScatterplotLayer<FirePoint>({
    id: 'fire-points',
    data,
    getPosition: (d) => d.position,
    getRadius: 400,
    radiusUnits: 'meters',
    getFillColor: (d) =>
      d.isViirs ? [255, 80, 0, 180] : [255, 160, 0, 140],
    stroked: false,
    pickable: false,
  });
}
