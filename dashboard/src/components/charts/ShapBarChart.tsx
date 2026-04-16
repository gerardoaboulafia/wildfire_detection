'use client';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { SHAP_FEATURE_LABELS } from '@/lib/constants';

interface ShapEntry {
  feature: string;
  mean_abs_shap: number;
}

interface Props {
  data: ShapEntry[];
}

// Colour by category
function barColor(feature: string): string {
  if (feature.startsWith('lc_')) return '#8b5cf6';
  if (feature.includes('distance')) return '#3b82f6';
  if (['elevation', 'slope', 'aspect_cos'].includes(feature)) return '#10b981';
  return '#f97316';
}

export default function ShapBarChart({ data }: Props) {
  const top10 = [...data]
    .sort((a, b) => b.mean_abs_shap - a.mean_abs_shap)
    .slice(0, 10)
    .map((d) => ({
      ...d,
      label: (SHAP_FEATURE_LABELS[d.feature] ?? d.feature)
        .replace(' (km)', '')
        .replace(' (m)', '')
        .replace(' (%)', '')
        .replace(' (°)', ''),
    }))
    .reverse(); // recharts renders bottom-to-top for horizontal bars

  return (
    <div className="h-full">
      <h3 className="mb-3 text-sm font-bold text-white">
        Feature Importance (mean |SHAP|)
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart
          data={top10}
          layout="vertical"
          margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickFormatter={(v) => v.toFixed(3)}
          />
          <YAxis
            dataKey="label"
            type="category"
            width={140}
            tick={{ fill: '#d1d5db', fontSize: 11 }}
          />
          <Tooltip
            formatter={(v: number) => [v.toFixed(5), 'mean |SHAP|']}
            contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#f3f4f6' }}
          />
          <Bar dataKey="mean_abs_shap" radius={[0, 4, 4, 0]}>
            {top10.map((entry) => (
              <Cell key={entry.feature} fill={barColor(entry.feature)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
