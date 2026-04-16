'use client';

import { useEffect, useRef } from 'react';
import MapContainer from '@/components/MapContainer';
import LoadingOverlay from '@/components/ui/LoadingOverlay';
import TimeSlider from '@/components/controls/TimeSlider';
import LayerToggleControls from '@/components/controls/LayerToggles';
import { useHeatmapLayer } from '@/components/layers/useHeatmapLayer';
import { useFirePointsLayer } from '@/components/layers/useFirePointsLayer';
import { useStore } from '@/store/useStore';

// Scripted flyover waypoints across Córdoba
const WAYPOINTS = [
  { center: [-64.2, -30.0] as [number, number], zoom: 8.5, pitch: 62, bearing: 25, duration: 5000 },
  { center: [-64.8, -31.5] as [number, number], zoom: 9, pitch: 55, bearing: -10, duration: 5000 },
  { center: [-63.5, -32.5] as [number, number], zoom: 8, pitch: 60, bearing: 40, duration: 5000 },
  { center: [-63.0, -33.8] as [number, number], zoom: 9, pitch: 58, bearing: 10, duration: 5000 },
  { center: [-63.78, -32.25] as [number, number], zoom: 7, pitch: 45, bearing: -10, duration: 4000 },
];

export default function FlyoverView() {
  const layers_store = useStore((s) => s.layers);
  const heatmapLayer = useHeatmapLayer(layers_store.showHeatmap);
  const fireLayer = useFirePointsLayer(layers_store.showFires);
  const flyoverStarted = useRef(false);

  // Trigger the flyover animation once the map is ready
  useEffect(() => {
    if (flyoverStarted.current) return;

    let cancelled = false;

    async function startFlyover() {
      // Wait for Mapbox to be loaded
      const mapboxgl = (await import('mapbox-gl')).default;
      void mapboxgl;

      // Poll until the map container has a Mapbox map attached
      // We access the global map instance via a custom event
      let attempts = 0;
      while (attempts < 30) {
        if (cancelled) return;
        await new Promise((r) => setTimeout(r, 500));
        attempts++;

        // Dispatch a custom event to trigger flyover from MapContainer
        window.dispatchEvent(new CustomEvent('wf:startFlyover', { detail: WAYPOINTS }));
        break;
      }
    }

    const timer = setTimeout(() => {
      if (!flyoverStarted.current) {
        flyoverStarted.current = true;
        startFlyover();
      }
    }, 2500);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <div className="relative flex h-full w-full">
      <div className="relative flex-1">
        <LoadingOverlay />
        <MapContainer layers={[heatmapLayer, fireLayer]} />

        {/* Flyover label */}
        <div className="pointer-events-none absolute bottom-8 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-4 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
          Terrain flyover — Córdoba Province fire risk
        </div>
      </div>

      <div className="flex w-52 flex-col gap-4 bg-gray-900 p-4">
        <div>
          <h2 className="mb-1 text-sm font-bold text-white">Terrain Flyover</h2>
          <p className="text-xs text-gray-400">
            Animated tour with heatmap showing susceptibility probability.
          </p>
        </div>
        <LayerToggleControls />
        <TimeSlider />
      </div>
    </div>
  );
}
