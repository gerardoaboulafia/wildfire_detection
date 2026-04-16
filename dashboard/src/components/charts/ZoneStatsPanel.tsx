'use client';

interface ZoneStat {
  risk_class: number;
  label: string;
  n_fires: number;
  pct: number;
}

interface Props {
  zonal_stats: ZoneStat[];
  area_km2: Record<string, number>;
  n_fires_total: number;
  pct_high_vh: number;
}

const COLORS: Record<string, string> = {
  Low: 'text-green-400',
  Moderate: 'text-yellow-400',
  High: 'text-orange-400',
  'Very High': 'text-red-400',
};

const BG: Record<string, string> = {
  Low: 'bg-green-600/20',
  Moderate: 'bg-yellow-600/20',
  High: 'bg-orange-600/20',
  'Very High': 'bg-red-600/20',
};

export default function ZoneStatsPanel({ zonal_stats, area_km2, n_fires_total, pct_high_vh }: Props) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold text-white">Zonal Validation Statistics</h3>

      {/* Validation badge */}
      <div className="mb-4 flex items-center gap-3 rounded-lg bg-green-900/30 p-3">
        <span className="text-2xl">✅</span>
        <div>
          <p className="text-sm font-bold text-green-400">
            {pct_high_vh.toFixed(1)}% of fires in High + Very High
          </p>
          <p className="text-xs text-gray-400">
            {n_fires_total.toLocaleString()} VIIRS 2023–2024 detections — target ≥80%
          </p>
        </div>
      </div>

      {/* Zone table */}
      <div className="overflow-hidden rounded-lg border border-gray-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800 text-xs uppercase tracking-wider text-gray-400">
              <th className="px-3 py-2 text-left">Zone</th>
              <th className="px-3 py-2 text-right">Area (km²)</th>
              <th className="px-3 py-2 text-right">Fires</th>
              <th className="px-3 py-2 text-right">% fires</th>
            </tr>
          </thead>
          <tbody>
            {[...zonal_stats].reverse().map((z) => (
              <tr key={z.risk_class} className={`border-t border-gray-700 ${BG[z.label] ?? ''}`}>
                <td className={`px-3 py-2 font-semibold ${COLORS[z.label] ?? 'text-white'}`}>
                  {z.label}
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-300">
                  {(area_km2[z.label] ?? 0).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-300">
                  {z.n_fires.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right font-mono text-white">
                  {z.pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
