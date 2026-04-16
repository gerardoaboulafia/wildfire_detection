'use client';

import { useStore } from '@/store/useStore';

const PRESETS = [2000, 5000, 8000, 15000, 30000];

export default function HexRadiusSlider() {
  const hexRadius = useStore((s) => s.hexRadius);
  const setHexRadius = useStore((s) => s.setHexRadius);

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Hex radius
      </p>
      <div className="flex gap-1">
        {PRESETS.map((r) => (
          <button
            key={r}
            onClick={() => setHexRadius(r)}
            className={`flex-1 rounded px-1 py-1 text-xs font-medium transition-colors ${
              hexRadius === r
                ? 'bg-orange-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {r >= 1000 ? `${r / 1000}km` : `${r}m`}
          </button>
        ))}
      </div>
    </div>
  );
}
