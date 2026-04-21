'use client';

import { useStore } from '@/store/useStore';

export default function LoadingOverlay() {
  const gridLoaded = useStore((s) => s.gridLoaded);
  const firesLoaded = useStore((s) => s.firesLoaded);

  if (gridLoaded && firesLoaded) return null;

  return (
    <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-gray-950/90 text-white">
      <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-orange-500 border-t-transparent" />
      <p className="text-lg font-semibold">Loading susceptibility data…</p>
      <p className="mt-1 text-sm text-gray-400">
        {!gridLoaded && 'Grid (4.2 MB) '}
        {!firesLoaded && 'Fire detections (631 KB)'}
      </p>
    </div>
  );
}
