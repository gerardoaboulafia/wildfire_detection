'use client';

import { useStore, BasemapStyle } from '@/store/useStore';

const OPTIONS: { id: BasemapStyle; label: string }[] = [
  { id: 'terrain', label: 'Terrain' },
  { id: 'satellite', label: 'Satellite' },
  { id: 'streets', label: 'Streets' },
];

export default function BasemapToggle() {
  const basemap = useStore((s) => s.basemap);
  const setBasemap = useStore((s) => s.setBasemap);

  return (
    <div>
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Basemap
      </p>
      <div className="flex gap-1">
        {OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setBasemap(opt.id)}
            className={`flex-1 rounded px-2 py-1 text-xs font-medium transition-colors ${
              basemap === opt.id
                ? 'bg-orange-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
