/** @type {import('next').NextConfig} */
const nextConfig = {
  // Deck.gl uses ESM — Next.js App Router needs explicit transpilation
  transpilePackages: [
    '@deck.gl/core',
    '@deck.gl/layers',
    '@deck.gl/aggregation-layers',
    '@deck.gl/extensions',
    '@deck.gl/mapbox',
  ],
};

export default nextConfig;
