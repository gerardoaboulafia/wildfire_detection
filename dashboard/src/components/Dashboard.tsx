'use client';

import { useStore } from '@/store/useStore';
import { useDataLoader } from '@/hooks/useDataLoader';
import Sidebar from '@/components/Sidebar';
import RiskExtrusionView from '@/components/views/RiskExtrusionView';
import HexbinView from '@/components/views/HexbinView';
import FlyoverView from '@/components/views/FlyoverView';
import AnalysisView from '@/components/views/AnalysisView';

export default function Dashboard() {
  // Load binary data on mount
  useDataLoader();

  const activeView = useStore((s) => s.activeView);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-gray-950">
      <Sidebar />

      <main className="relative flex-1 overflow-hidden">
        {/* Views 1-3 share a map; analysis is pure charts.
            We unmount map views (not just hide) to free GPU when on analysis. */}
        {activeView === 'risk-extrusion' && <RiskExtrusionView />}
        {activeView === 'hexbin' && <HexbinView />}
        {activeView === 'flyover' && <FlyoverView />}
        {activeView === 'analysis' && <AnalysisView />}
      </main>
    </div>
  );
}
