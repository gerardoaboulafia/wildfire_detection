'use client';

import { useStore, ViewId } from '@/store/useStore';

const NAV_ITEMS: { id: ViewId; label: string; icon: string; desc: string }[] = [
  { id: 'risk-extrusion', label: 'Risk Heatmap', icon: '🔥', desc: 'Susceptibility surface' },
  { id: 'hexbin', label: 'Fire Density', icon: '⬡', desc: 'Detection heatmap' },
  { id: 'flyover', label: 'Flyover', icon: '✈', desc: 'Terrain animation' },
  { id: 'analysis', label: 'Analysis', icon: '📊', desc: 'Charts & metrics' },
];

export default function Sidebar() {
  const activeView = useStore((s) => s.activeView);
  const setActiveView = useStore((s) => s.setActiveView);

  return (
    <nav className="flex h-full w-48 flex-col border-r border-gray-800 bg-gray-950 py-4">
      {/* Logo / title */}
      <div className="px-4 pb-4">
        <h1 className="text-xs font-bold uppercase tracking-widest text-orange-500">
          Wildfire Risk
        </h1>
        <p className="mt-0.5 text-xs text-gray-500">Córdoba, Argentina</p>
      </div>

      <div className="h-px bg-gray-800" />

      {/* Nav buttons */}
      <div className="mt-4 flex flex-col gap-1 px-2">
        {NAV_ITEMS.map(({ id, label, icon, desc }) => (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            className={`flex flex-col rounded-lg px-3 py-2.5 text-left transition-colors ${
              activeView === id
                ? 'bg-orange-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <span className="text-base">{icon}</span>
            <span className="mt-0.5 text-xs font-semibold">{label}</span>
            <span
              className={`text-xs ${activeView === id ? 'text-orange-200' : 'text-gray-600'}`}
            >
              {desc}
            </span>
          </button>
        ))}
      </div>

      {/* Bottom AUC badge */}
      <div className="mt-auto px-4">
        <div className="rounded-lg bg-gray-900 p-3 text-center">
          <p className="text-xs text-gray-500">Best model (RF)</p>
          <p className="mt-1 font-mono text-lg font-bold text-orange-400">AUC 0.698</p>
          <p className="text-xs text-gray-500">87.3% zonal validation</p>
        </div>
      </div>
    </nav>
  );
}
