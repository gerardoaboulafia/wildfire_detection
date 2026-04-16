'use client';

import { useMemo } from 'react';
import { ColumnLayer } from '@deck.gl/layers';
import { useStore } from '@/store/useStore';
import { RISK_COLORS } from '@/lib/colorScales';

interface GridPoint {
  position: [number, number];
  prob: number;
  cls: number;
}

export function useGridLayer(enabled: boolean) {
  const gridLons = useStore((s) => s.gridLons);
  const gridLats = useStore((s) => s.gridLats);
  const gridProbs = useStore((s) => s.gridProbs);
  const gridClasses = useStore((s) => s.gridClasses);
  const setPopup = useStore((s) => s.setPopup);
  const shapSamples = useStore((s) => s.shapSamples);

  const data = useMemo<GridPoint[]>(() => {
    if (!gridLons || !gridLats || !gridProbs || !gridClasses) return [];
    const n = gridLons.length;
    const arr: GridPoint[] = new Array(n);
    for (let i = 0; i < n; i++) {
      arr[i] = {
        position: [gridLons[i], gridLats[i]],
        prob: gridProbs[i],
        cls: gridClasses[i],
      };
    }
    return arr;
  }, [gridLons, gridLats, gridProbs, gridClasses]);

  if (!enabled || data.length === 0) return null;

  return new ColumnLayer<GridPoint>({
    id: 'risk-columns',
    data,
    diskResolution: 6,   // hexagonal prisms
    radius: 250,         // 250m → fills 500m grid with slight gap
    extruded: true,
    getPosition: (d) => d.position,
    getElevation: (d) => d.prob * 8000,   // max ~8km visual height at prob=1
    getFillColor: (d) => RISK_COLORS[d.cls] ?? [128, 128, 128, 180],
    getLineColor: [0, 0, 0, 0],
    material: { ambient: 0.4, diffuse: 0.6, shininess: 16 },
    pickable: true,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 60],
    onClick: (info) => {
      if (!info.object) return;
      const d = info.object as GridPoint;

      let shapValues: Record<string, number> | null = null;
      if (shapSamples && shapSamples.length > 0) {
        // Return a representative sample matching fire vs non-fire class
        const classMatch = shapSamples.filter(
          (s) => (d.prob > 0.5 ? s.label === 1 : s.label === 0),
        );
        if (classMatch.length > 0) {
          const raw = classMatch[Math.floor(Math.random() * classMatch.length)] as Record<string, number>;
          const { label: _l, pred_prob: _p, ...feats } = raw;
          void _l; void _p;
          shapValues = feats;
        }
      }

      setPopup({
        lon: d.position[0],
        lat: d.position[1],
        prob: d.prob,
        cls: d.cls,
        shapValues,
      });
    },
  });
}
