'use client';

import { useEffect, useRef } from 'react';
import type { Layer } from '@deck.gl/core';
import { useStore } from '@/store/useStore';
import { INITIAL_VIEW_STATE, MAPBOX_STYLES } from '@/lib/constants';

interface Props {
  layers: (Layer | null)[];
  enableTerrain?: boolean;
}

export default function MapContainer({ layers, enableTerrain = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<unknown>(null);
  const overlayRef = useRef<unknown>(null);
  const layersRef = useRef(layers);
  const basemap = useStore((s) => s.basemap);
  const basemapRef = useRef(basemap);
  const enableTerrainRef = useRef(enableTerrain);

  useEffect(() => {
    layersRef.current = layers;
  });

  useEffect(() => {
    if (!containerRef.current) return;
    let map: unknown;
    let overlay: unknown;

    async function init() {
      const mapboxgl = (await import('mapbox-gl')).default;
      const { MapboxOverlay } = await import('@deck.gl/mapbox');

      mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? '';

      map = new mapboxgl.Map({
        container: containerRef.current!,
        style: MAPBOX_STYLES[basemapRef.current],
        center: [INITIAL_VIEW_STATE.longitude, INITIAL_VIEW_STATE.latitude],
        zoom: INITIAL_VIEW_STATE.zoom,
        pitch: INITIAL_VIEW_STATE.pitch,
        bearing: INITIAL_VIEW_STATE.bearing,
        antialias: true,
      });

      (map as mapboxgl.Map).on('load', () => {
        const m = map as mapboxgl.Map;

        if (enableTerrainRef.current) {
          m.addSource('mapbox-dem', {
            type: 'raster-dem',
            url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
            tileSize: 512,
            maxzoom: 14,
          });
          m.setTerrain({ source: 'mapbox-dem', exaggeration: 2.0 });

          m.addLayer({
            id: 'sky',
            type: 'sky',
            paint: {
              'sky-type': 'atmosphere',
              'sky-atmosphere-sun': [0.0, 90.0],
              'sky-atmosphere-sun-intensity': 15,
            },
          });
        }

        overlay = new MapboxOverlay({
          layers: layersRef.current.filter(Boolean) as Layer[],
        });
        (map as mapboxgl.Map).addControl(overlay as mapboxgl.IControl);
        overlayRef.current = overlay;

        function handleFlyover(e: Event) {
          const waypoints = (e as CustomEvent).detail as {
            center: [number, number]; zoom: number; pitch: number; bearing: number; duration: number;
          }[];
          if (!waypoints?.length) return;

          let i = 0;
          function flyNext() {
            if (i >= waypoints.length) return;
            const wp = waypoints[i++];
            m.flyTo({
              center: wp.center,
              zoom: wp.zoom,
              pitch: wp.pitch,
              bearing: wp.bearing,
              duration: wp.duration,
              essential: true,
            });
            m.once('moveend', flyNext);
          }
          flyNext();
        }
        window.addEventListener('wf:startFlyover', handleFlyover);
      });

      mapRef.current = map;
    }

    init().catch(console.error);

    return () => {
      (map as mapboxgl.Map | undefined)?.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!overlayRef.current) return;
    const validLayers = layers.filter(Boolean) as Layer[];
    (overlayRef.current as { setProps: (p: object) => void }).setProps({ layers: validLayers });
  }, [layers]);

  useEffect(() => {
    const map = mapRef.current as mapboxgl.Map | null;
    if (!map) return;
    basemapRef.current = basemap;

    async function switchStyle() {
      map!.setStyle(MAPBOX_STYLES[basemap]);
      map!.once('styledata', () => {
        if (enableTerrainRef.current) {
          if (!map!.getSource('mapbox-dem')) {
            map!.addSource('mapbox-dem', {
              type: 'raster-dem',
              url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
              tileSize: 512,
              maxzoom: 14,
            });
          }
          map!.setTerrain({ source: 'mapbox-dem', exaggeration: 2.0 });
        }
      });
    }

    switchStyle().catch(console.error);
  }, [basemap]);

  return <div ref={containerRef} className="w-full h-full" />;
}
