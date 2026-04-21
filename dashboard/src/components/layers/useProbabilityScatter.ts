'use client';

import { useMemo } from 'react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { useStore } from '@/store/useStore';

// Matplotlib RdYlGn_r control points (inverted so high prob = red).
// Source: matplotlib._cm._RdYlGn_data, reversed.
const RAMP: [number, number, number, number][] = [
  [0.0,   0,   104, 55],
  [0.125, 26,  152, 80],
  [0.25,  102, 189, 99],
  [0.375, 166, 217, 106],
  [0.5,   255, 255, 191],
  [0.625, 254, 224, 139],
  [0.75,  253, 174, 97],
  [0.875, 244, 109, 67],
  [1.0,   165, 0,   38],
];

function rdYlGnR(t: number): [number, number, number] {
  if (t <= 0) return [RAMP[0][1], RAMP[0][2], RAMP[0][3]];
  if (t >= 1) {
    const last = RAMP[RAMP.length - 1];
    return [last[1], last[2], last[3]];
  }
  for (let i = 0; i < RAMP.length - 1; i++) {
    const [t0, r0, g0, b0] = RAMP[i];
    const [t1, r1, g1, b1] = RAMP[i + 1];
    if (t <= t1) {
      const f = (t - t0) / (t1 - t0);
      return [
        Math.round(r0 + f * (r1 - r0)),
        Math.round(g0 + f * (g1 - g0)),
        Math.round(b0 + f * (b1 - b0)),
      ];
    }
  }
  return [0, 0, 0];
}

export function useProbabilityScatter(enabled: boolean, alpha = 180) {
  const gridLons = useStore((s) => s.gridLons);
  const gridLats = useStore((s) => s.gridLats);
  const gridProbs = useStore((s) => s.gridProbs);

  // Pack into typed-array attribute buffers so deck.gl uploads directly to GPU.
  const attrs = useMemo(() => {
    if (!gridLons || !gridLats || !gridProbs) return null;
    const n = gridLons.length;
    const positions = new Float32Array(n * 2);
    const colors = new Uint8Array(n * 4);
    for (let i = 0; i < n; i++) {
      positions[i * 2] = gridLons[i];
      positions[i * 2 + 1] = gridLats[i];
      const [r, g, b] = rdYlGnR(gridProbs[i]);
      colors[i * 4] = r;
      colors[i * 4 + 1] = g;
      colors[i * 4 + 2] = b;
      colors[i * 4 + 3] = alpha;
    }
    return { n, positions, colors };
  }, [gridLons, gridLats, gridProbs, alpha]);

  if (!enabled || !attrs) return null;

  return new ScatterplotLayer({
    id: 'probability-scatter',
    data: {
      length: attrs.n,
      attributes: {
        getPosition: { value: attrs.positions, size: 2 },
        getFillColor: { value: attrs.colors, size: 4 },
      },
    },
    getRadius: 350,
    radiusUnits: 'meters',
    radiusMinPixels: 1.2,
    radiusMaxPixels: 20,
    stroked: false,
    pickable: false,
    // Cells naturally overlap at low zoom → smooth heatmap-like blend.
  });
}
