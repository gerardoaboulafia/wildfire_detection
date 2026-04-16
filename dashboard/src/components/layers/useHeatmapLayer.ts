'use client';

import { useMemo } from 'react';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { useStore } from '@/store/useStore';

interface HeatPoint {
  position: [number, number];
  weight: number;
}

// Sample every Nth point — 630K/8 ≈ 79K points, plenty for a smooth heatmap
const SAMPLE_RATE = 8;

export function useHeatmapLayer(enabled: boolean) {
  const gridLons = useStore((s) => s.gridLons);
  const gridLats = useStore((s) => s.gridLats);
  const gridProbs = useStore((s) => s.gridProbs);

  const data = useMemo<HeatPoint[]>(() => {
    if (!gridLons || !gridLats || !gridProbs) return [];
    const n = gridLons.length;
    const arr: HeatPoint[] = [];
    for (let i = 0; i < n; i += SAMPLE_RATE) {
      arr.push({
        position: [gridLons[i], gridLats[i]],
        weight: gridProbs[i],
      });
    }
    return arr;
  }, [gridLons, gridLats, gridProbs]);

  if (!enabled || data.length === 0) return null;

  return new HeatmapLayer<HeatPoint>({
    id: 'susceptibility-heatmap',
    data,
    getPosition: (d) => d.position,
    getWeight: (d) => d.weight,
    radiusPixels: 35,
    intensity: 1.4,
    threshold: 0.03,
    colorRange: [
      [34, 197, 94],
      [234, 179, 8],
      [249, 115, 22],
      [220, 38, 38],
      [139, 0, 0],
    ],
  });
}
