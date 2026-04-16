'use client';

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

interface FireEntry {
  year: number;
  count: number;
  source: 'MODIS' | 'VIIRS';
}

interface Props {
  data: FireEntry[];
}

export default function FireTimeline({ data }: Props) {
  // Pivot: one row per year with MODIS and VIIRS columns
  const byYear: Record<number, { year: number; MODIS: number; VIIRS: number }> = {};
  for (const d of data) {
    if (!byYear[d.year]) byYear[d.year] = { year: d.year, MODIS: 0, VIIRS: 0 };
    byYear[d.year][d.source] = d.count;
  }
  const chartData = Object.values(byYear).sort((a, b) => a.year - b.year);

  return (
    <div className="h-full">
      <h3 className="mb-3 text-sm font-bold text-white">
        Annual Fire Detections 2001–2024
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <AreaChart data={chartData} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
          <defs>
            <linearGradient id="modis" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.6} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="viirs" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.7} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="year" tick={{ fill: '#9ca3af', fontSize: 11 }} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#f3f4f6' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#d1d5db' }} />
          <Area
            type="monotone"
            dataKey="MODIS"
            stroke="#f97316"
            fill="url(#modis)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="VIIRS"
            stroke="#ef4444"
            fill="url(#viirs)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
