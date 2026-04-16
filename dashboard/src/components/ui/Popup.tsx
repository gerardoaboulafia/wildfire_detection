'use client';

import { useStore } from '@/store/useStore';
import { CLASS_LABELS, SHAP_FEATURE_LABELS } from '@/lib/constants';
import { RISK_COLORS } from '@/lib/colorScales';

const CLASS_BG: Record<number, string> = {
  1: 'bg-green-600',
  2: 'bg-yellow-500',
  3: 'bg-orange-500',
  4: 'bg-red-600',
};

export default function Popup() {
  const popup = useStore((s) => s.popup);
  const setPopup = useStore((s) => s.setPopup);

  if (!popup) return null;

  const color = RISK_COLORS[popup.cls] ?? [128, 128, 128, 255];
  const topShap = popup.shapValues
    ? Object.entries(popup.shapValues)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 6)
    : [];

  const maxAbs = topShap.length > 0 ? Math.max(...topShap.map(([, v]) => Math.abs(v))) : 1;

  return (
    <div className="absolute right-4 top-4 z-40 w-72 rounded-xl bg-gray-900/95 p-4 shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <span
          className={`rounded-full px-3 py-1 text-sm font-bold text-white ${CLASS_BG[popup.cls] ?? 'bg-gray-600'}`}
        >
          {CLASS_LABELS[popup.cls] ?? 'Unknown'} Risk
        </span>
        <button
          onClick={() => setPopup(null)}
          className="text-gray-400 hover:text-white"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Probability bar */}
      <div className="mb-4">
        <div className="mb-1 flex justify-between text-xs text-gray-400">
          <span>Susceptibility probability</span>
          <span className="font-mono font-bold text-white">
            {(popup.prob * 100).toFixed(1)}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-700">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${popup.prob * 100}%`,
              backgroundColor: `rgb(${color[0]},${color[1]},${color[2]})`,
            }}
          />
        </div>
      </div>

      {/* Coordinates */}
      <div className="mb-3 font-mono text-xs text-gray-500">
        {popup.lat.toFixed(4)}°S, {Math.abs(popup.lon).toFixed(4)}°W
      </div>

      {/* Local SHAP explanation */}
      {topShap.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
            Top drivers (SHAP)
          </p>
          <div className="space-y-1.5">
            {topShap.map(([feat, val]) => (
              <div key={feat} className="flex items-center gap-2">
                <span className="w-28 truncate text-right text-xs text-gray-300">
                  {SHAP_FEATURE_LABELS[feat]?.split(' ')[0] ?? feat}
                </span>
                <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-gray-700">
                  <div
                    className="absolute inset-y-0 rounded-full"
                    style={{
                      left: val >= 0 ? '50%' : `${50 - (Math.abs(val) / maxAbs) * 50}%`,
                      right: val < 0 ? '50%' : `${50 - (val / maxAbs) * 50}%`,
                      backgroundColor: val >= 0 ? 'rgb(239,68,68)' : 'rgb(59,130,246)',
                    }}
                  />
                </div>
                <span
                  className={`w-10 text-right font-mono text-xs ${val >= 0 ? 'text-red-400' : 'text-blue-400'}`}
                >
                  {val >= 0 ? '+' : ''}{val.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
