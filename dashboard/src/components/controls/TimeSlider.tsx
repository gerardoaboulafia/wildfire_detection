'use client';

import { useStore } from '@/store/useStore';

export default function TimeSlider() {
  const yearRange = useStore((s) => s.yearRange);
  const setYearRange = useStore((s) => s.setYearRange);

  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-gray-400">
        <span className="font-semibold uppercase tracking-wider">Year range</span>
        <span className="font-mono text-white">
          {yearRange[0]} – {yearRange[1]}
        </span>
      </div>
      <div className="space-y-1">
        <input
          type="range"
          min={2001}
          max={yearRange[1]}
          value={yearRange[0]}
          onChange={(e) => setYearRange([+e.target.value, yearRange[1]])}
          className="w-full accent-orange-500"
        />
        <input
          type="range"
          min={yearRange[0]}
          max={2024}
          value={yearRange[1]}
          onChange={(e) => setYearRange([yearRange[0], +e.target.value])}
          className="w-full accent-orange-500"
        />
      </div>
    </div>
  );
}
