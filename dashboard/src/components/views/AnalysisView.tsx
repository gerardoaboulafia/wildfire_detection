'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import ShapBarChart from '@/components/charts/ShapBarChart';
import FireTimeline from '@/components/charts/FireTimeline';
import ZoneStatsPanel from '@/components/charts/ZoneStatsPanel';
import ConfusionMatrix from '@/components/charts/ConfusionMatrix';

interface Stats {
  validation: {
    n_fires_total: number;
    pct_high_vh: number;
    zonal_stats: { risk_class: number; label: string; n_fires: number; pct: number }[];
  };
  models: {
    model: string; cv_auc: number; test_auc: number;
    test_accuracy: number; test_precision: number; test_recall: number; test_f1: number;
  }[];
  area_km2: Record<string, number>;
}

export default function AnalysisView() {
  const [shapData, setShapData] = useState<{ feature: string; mean_abs_shap: number }[]>([]);
  const [fireData, setFireData] = useState<{ year: number; count: number; source: 'MODIS' | 'VIIRS' }[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    Promise.all([
      fetch('/data/shap_global.json').then((r) => r.json()),
      fetch('/data/annual_fires.json').then((r) => r.json()),
      fetch('/data/stats.json').then((r) => r.json()),
    ]).then(([shap, fires, st]) => {
      setShapData(shap);
      setFireData(fires);
      setStats(st);
    }).catch(console.error);
  }, []);

  if (!stats) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        Loading analysis data…
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-950 p-6">
      <h1 className="mb-6 text-xl font-bold text-white">
        Wildfire Susceptibility — Analysis Dashboard
        <span className="ml-3 text-sm font-normal text-gray-400">Córdoba Province, Argentina</span>
      </h1>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* SHAP feature importance */}
        <div className="rounded-xl bg-gray-900 p-5" style={{ height: 380 }}>
          {shapData.length > 0 && <ShapBarChart data={shapData} />}
        </div>

        {/* Zonal validation stats */}
        <div className="rounded-xl bg-gray-900 p-5">
          <ZoneStatsPanel
            zonal_stats={stats.validation.zonal_stats}
            area_km2={stats.area_km2}
            n_fires_total={stats.validation.n_fires_total}
            pct_high_vh={stats.validation.pct_high_vh}
          />
        </div>

        {/* Fire timeline */}
        <div className="rounded-xl bg-gray-900 p-5" style={{ height: 320 }}>
          {fireData.length > 0 && <FireTimeline data={fireData} />}
        </div>

        {/* Model metrics */}
        <div className="rounded-xl bg-gray-900 p-5">
          <ConfusionMatrix models={stats.models} />

          {/* ROC Curve */}
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-bold text-white">ROC Curves (tuned models)</h3>
            <div className="relative overflow-hidden rounded-lg" style={{ height: 180 }}>
              <Image
                src="/data/roc_curves.png"
                alt="ROC curves for RF, XGBoost, LightGBM"
                fill
                className="object-contain"
                unoptimized
              />
            </div>
          </div>
        </div>
      </div>

      {/* Footer note */}
      <p className="mt-6 text-xs text-gray-600">
        Models trained on MODIS FIRMS 2001–2022 with 10-fold spatial GroupKFold CV.
        Validated against VIIRS VNP14IMG 2023–2024 (independent temporal holdout).
        Risk classification via Natural Breaks (Jenks, k=4).
      </p>
    </div>
  );
}
