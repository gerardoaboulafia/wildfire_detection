'use client';

import MapContainer from '@/components/MapContainer';
import LoadingOverlay from '@/components/ui/LoadingOverlay';
import TimeSlider from '@/components/controls/TimeSlider';
import BasemapToggle from '@/components/controls/BasemapToggle';
import { useFireDensityLayer } from '@/components/layers/useFireDensityLayer';

export default function HexbinView() {
  const fireDensityLayer = useFireDensityLayer(true);

  return (
    <div className="relative flex h-full w-full">
      <div className="relative flex-1">
        <LoadingOverlay />
        <MapContainer layers={[fireDensityLayer]} enableTerrain={false} />
      </div>

      <div className="flex w-52 flex-col gap-4 bg-gray-900 p-4">
        <div>
          <h2 className="mb-1 text-sm font-bold text-white">Fire Density</h2>
          <p className="text-xs text-gray-400">
            Heatmap of 63,134 fire detections (2001–2024). Filter by year range.
          </p>
        </div>
        <BasemapToggle />
        <TimeSlider />
        <div className="mt-auto rounded-lg bg-gray-800 p-3 text-xs text-gray-400">
          <p className="mb-1">
            <span className="font-bold text-orange-400">MODIS</span> 2001–2022
          </p>
          <p>
            <span className="font-bold text-red-400">VIIRS</span> 2023–2024
          </p>
        </div>
      </div>
    </div>
  );
}
