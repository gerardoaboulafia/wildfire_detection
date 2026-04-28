'use client';

import MapContainer from '@/components/MapContainer';
import LoadingOverlay from '@/components/ui/LoadingOverlay';
import BasemapToggle from '@/components/controls/BasemapToggle';
import LayerToggleControls from '@/components/controls/LayerToggles';
import RiskOpacitySlider from '@/components/controls/RiskOpacitySlider';
import { useProbabilityScatter } from '@/components/layers/useProbabilityScatter';
import { useFirePointsLayer } from '@/components/layers/useFirePointsLayer';
import { useZonesLayer } from '@/components/layers/useZonesLayer';
import { useStore } from '@/store/useStore';

export default function RiskExtrusionView() {
  const layers = useStore((s) => s.layers);
  const probLayer = useProbabilityScatter(true);
  const fireLayer = useFirePointsLayer(layers.showFires);
  const zonesLayer = useZonesLayer(layers.showZones);

  const deckLayers = [probLayer, zonesLayer, fireLayer];

  return (
    <div className="relative flex h-full w-full">
      <div className="relative flex-1">
        <LoadingOverlay />
        <MapContainer layers={deckLayers} enableTerrain={false} />

        {/* Continuous RdYlGn_r gradient legend — matches the notebook colorbar */}
        <div className="absolute bottom-8 left-4 rounded-xl bg-gray-900/90 p-3 text-xs">
          <p className="mb-2 font-semibold uppercase tracking-wider text-gray-400">
            Susceptibility
          </p>
          <div
            className="h-3 w-40 rounded-sm"
            style={{
              background:
                'linear-gradient(to right, rgb(0,104,55), rgb(102,189,99), rgb(255,255,191), rgb(253,174,97), rgb(165,0,38))',
            }}
          />
          <div className="mt-1 flex w-40 justify-between text-gray-400">
            <span>0.0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex w-52 flex-col gap-4 bg-gray-900 p-4">
        <div>
          <h2 className="mb-1 text-sm font-bold text-white">Risk Map</h2>
          <p className="text-xs text-gray-400">
            Continuous susceptibility probability across Córdoba. Green = low risk, red = high risk.
          </p>
        </div>
        <BasemapToggle />
        <LayerToggleControls />
        <RiskOpacitySlider />
        <div className="mt-auto rounded-lg bg-gray-800 p-3">
          <p className="text-xs text-gray-400">
            <span className="font-mono font-bold text-white">629,777</span> grid cells at 500 m ·
            RF v2
          </p>
        </div>
      </div>
    </div>
  );
}
