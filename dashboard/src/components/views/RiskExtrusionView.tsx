'use client';

import MapContainer from '@/components/MapContainer';
import LoadingOverlay from '@/components/ui/LoadingOverlay';
import BasemapToggle from '@/components/controls/BasemapToggle';
import LayerToggleControls from '@/components/controls/LayerToggles';
import { useFirePointsLayer } from '@/components/layers/useFirePointsLayer';
import { useHeatmapLayer } from '@/components/layers/useHeatmapLayer';
import { useZonesLayer } from '@/components/layers/useZonesLayer';
import { useStore } from '@/store/useStore';

// Legend matching the heatmap color ramp
const LEGEND = [
  { label: 'Very High', color: 'bg-red-800' },
  { label: 'High', color: 'bg-red-600' },
  { label: 'Moderate', color: 'bg-orange-500' },
  { label: 'Low', color: 'bg-yellow-500' },
  { label: 'Very Low', color: 'bg-green-500' },
];

export default function RiskExtrusionView() {
  const layers = useStore((s) => s.layers);
  const fireLayer = useFirePointsLayer(layers.showFires);
  const heatmapLayer = useHeatmapLayer(true);
  const zonesLayer = useZonesLayer(layers.showZones);

  const deckLayers = [zonesLayer, heatmapLayer, fireLayer];

  return (
    <div className="relative flex h-full w-full">
      <div className="relative flex-1">
        <LoadingOverlay />
        <MapContainer layers={deckLayers} />

        {/* Legend */}
        <div className="absolute bottom-8 left-4 rounded-xl bg-gray-900/90 p-3 text-xs">
          <p className="mb-2 font-semibold uppercase tracking-wider text-gray-400">
            Risk level
          </p>
          {LEGEND.map(({ label, color }) => (
            <div key={label} className="mb-1 flex items-center gap-2">
              <div className={`h-3 w-3 rounded-sm ${color}`} />
              <span className="text-gray-200">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex w-52 flex-col gap-4 bg-gray-900 p-4">
        <div>
          <h2 className="mb-1 text-sm font-bold text-white">Risk Heatmap</h2>
          <p className="text-xs text-gray-400">
            Susceptibility probability across Córdoba. Warm colors = higher fire risk.
          </p>
        </div>
        <BasemapToggle />
        <LayerToggleControls />
        <div className="mt-auto rounded-lg bg-gray-800 p-3">
          <p className="text-xs text-gray-400">
            <span className="font-mono font-bold text-white">629,777</span> grid cells at 500m
            resolution.
          </p>
        </div>
      </div>
    </div>
  );
}
