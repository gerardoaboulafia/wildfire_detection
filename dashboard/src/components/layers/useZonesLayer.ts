'use client';

import { useMemo, useState, useEffect } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { ZONE_FILL_COLORS } from '@/lib/colorScales';

type GeoJSON = GeoJSON.FeatureCollection;

export function useZonesLayer(enabled: boolean) {
  const [geojson, setGeojson] = useState<GeoJSON | null>(null);

  useEffect(() => {
    fetch('/data/zones_simplified.geojson')
      .then((r) => r.json())
      .then(setGeojson)
      .catch(console.error);
  }, []);

  return useMemo(() => {
    if (!enabled || !geojson) return null;

    return new GeoJsonLayer({
      id: 'risk-zones',
      data: geojson,
      filled: true,
      stroked: false,
      getFillColor: (f) => {
        const label = f.properties?.label ?? f.properties?.risk_label ?? '';
        return ZONE_FILL_COLORS[label] ?? [128, 128, 128, 100];
      },
      pickable: false,
    });
  }, [enabled, geojson]);
}
