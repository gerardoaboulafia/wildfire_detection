import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Wildfire Susceptibility — Córdoba, Argentina',
  description:
    'Interactive 3D dashboard for wildfire susceptibility mapping in Córdoba Province. Built with Next.js, Deck.gl, and Mapbox GL.',
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-white`}>{children}</body>
    </html>
  );
}
