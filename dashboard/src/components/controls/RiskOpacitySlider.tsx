'use client';

import { useStore } from '@/store/useStore';

export default function RiskOpacitySlider() {
  const riskOpacity = useStore((s) => s.riskOpacity);
  const setRiskOpacity = useStore((s) => s.setRiskOpacity);

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Risk opacity
        </p>
        <span className="font-mono text-xs text-gray-300">
          {Math.round(riskOpacity * 100)}%
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={riskOpacity}
        onChange={(e) => setRiskOpacity(parseFloat(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-700 accent-orange-500"
      />
    </div>
  );
}
