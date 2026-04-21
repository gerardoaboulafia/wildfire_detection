'use client';

import { useMemo } from 'react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { useStore } from '@/store/useStore';

interface FirePoint {
  position: [number, number];
  year: number;
  isViirs: boolean;
}

const MAX_POINTS = 10_000;

export function useFirePointsLayer(enabled: boolean) {
  const fireLons = useStore((s) => s.fireLons);
  const fireLats = useStore((s) => s.fireLats);
  const fireYearOffsets = useStore((s) => s.fireYearOffsets);
  const nModisFires = useStore((s) => s.nModisFires);
  const yearRange = useStore((s) => s.yearRange);

  const data = useMemo<FirePoint[]>(() => {
    if (!fireLons || !fireLats || !fireYearOffsets) return [];
    const n = fireLons.length;
    const [yMin, yMax] = yearRange;
    const isFullRange = yMin === 2001 && yMax === 2024;

    // Collect indices that pass the year filter first
    const filtered: number[] = [];
    for (let i = 0; i < n; i++) {
      const year = 2000 + fireYearOffsets[i];
      if (year >= yMin && year <= yMax) filtered.push(i);
    }

    // When the full range is active decimate to ~10 K points; narrow ranges show all
    const stride = isFullRange ? Math.max(1, Math.floor(filtered.length / MAX_POINTS)) : 1;

    const arr: FirePoint[] = [];
    for (let j = 0; j < filtered.length; j += stride) {
      const i = filtered[j];
      arr.push({
        position: [fireLons[i], fireLats[i]],
        year: 2000 + fireYearOffsets[i],
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
    getRadius: 150,
    radiusUnits: 'meters',
    radiusMinPixels: 1,
    radiusMaxPixels: 3,
    getFillColor: (d) =>
      d.isViirs ? [255, 80, 0, 200] : [255, 160, 0, 160],
    stroked: false,
    pickable: false,
  });
}
