'use client';

import { useStore, LayerToggles } from '@/store/useStore';

const TOGGLES: { key: keyof LayerToggles; label: string }[] = [
  { key: 'showFires', label: 'Fire detections' },
  { key: 'showZones', label: 'Risk zone borders' },
];

export default function LayerToggleControls() {
  const layers = useStore((s) => s.layers);
  const toggleLayer = useStore((s) => s.toggleLayer);

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Layers
      </p>
      <div className="space-y-1">
        {TOGGLES.map(({ key, label }) => (
          <label key={key} className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={layers[key]}
              onChange={() => toggleLayer(key)}
              className="accent-orange-500"
            />
            <span className="text-sm text-gray-300">{label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
