/**
 * The sign-in panel's picture (2026-10-10): the world drawn as a honeycomb,
 * with the places consent is collected lit up and joined to one hub, and a
 * faint honeycomb behind the whole panel.
 *
 * Decorative throughout - hidden from assistive technology - and still under
 * `prefers-reduced-motion` (the motion is in `styles/auth.css`). The paths are
 * built once at module load from `WORLD_HEX`, so a render costs nothing.
 */
import * as React from "react";

import { WORLD_HEX } from "@/components/ui/world-hex-data";

/* Geometry: pointy-top hexagons, one column `W` wide. */
const W = 10;
const R = W / Math.sqrt(3);
const ROW_H = 1.5 * R;
const CELL_R = R * 0.84; // drawn a little small, so the cells read as tiles
const WIDTH = WORLD_HEX.cols * W + W / 2;
const HEIGHT = WORLD_HEX.rows.length * ROW_H + R / 2;

function hexPath(cx: number, cy: number, r: number): string {
  let d = "";
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 180) * (60 * i - 90);
    d += `${i ? "L" : "M"}${(cx + r * Math.cos(a)).toFixed(1)} ${(cy + r * Math.sin(a)).toFixed(1)}`;
  }
  return `${d}Z`;
}

function project(lon: number, lat: number): [number, number] {
  return [((lon + 180) / WORLD_HEX.step) * W, ((WORLD_HEX.lat0 - lat) / WORLD_HEX.rowStep) * ROW_H + R];
}

/** Where the arcs meet: Bengaluru, Karnataka, where the product is run from. */
const HUB = project(77.6, 13);

/* India and, inside it, Karnataka - outlines in degrees, simplified to the
   scale of a 3-degree cell. Their cells are drawn in their own colours. */
const INDIA: [number, number][] = [
  [68, 24], [71, 27], [74, 31], [76, 35], [79, 35], [80, 31], [84, 28], [88, 27],
  [89, 26], [92, 27], [97, 28], [95, 24], [92, 22], [88, 22], [86, 20], [80, 15],
  [80, 10], [77, 8], [73, 17], [72, 21],
];
const KARNATAKA: [number, number][] = [
  [74, 15.8], [76.5, 18.4], [77.6, 17.6], [78.6, 15.5], [78.5, 12.5], [77, 11.4],
  [75.3, 12], [74.3, 14],
];

function inside([x, y]: [number, number], poly: [number, number][]): boolean {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[j];
    if (y1 > y !== y2 > y && x < ((x2 - x1) * (y - y1)) / (y2 - y1) + x1) hit = !hit;
  }
  return hit;
}
/** The places the arcs reach: Samsung's sites around the world - its head
 *  office and R&D centres, and the regional offices - at city precision, for
 *  the picture only. */
const NODES = [
  [127.0, 37.3], // Suwon, head office
  [77.4, 28.5], // Noida
  [90.4, 23.8], // Dhaka
  [116.4, 39.9], // Beijing
  [118.8, 32.1], // Nanjing
  [139.6, 35.5], // Tokyo
  [105.8, 21.0], // Hanoi
  [106.8, -6.2], // Jakarta
  [151.2, -33.9], // Sydney
  [55.3, 25.2], // Dubai
  [34.8, 32.1], // Tel Aviv
  [31.2, 30.0], // Cairo
  [28.0, -26.2], // Johannesburg
  [37.6, 55.8], // Moscow
  [30.5, 50.5], // Kyiv
  [21.0, 52.2], // Warsaw
  [8.6, 50.1], // Frankfurt
  [2.35, 48.9], // Paris
  [-0.5, 51.4], // Staines, UK
  [-73.6, 45.5], // Montreal
  [-79.4, 43.7], // Toronto
  [-74.0, 40.7], // New York
  [-96.7, 33.0], // Plano
  [-122.1, 37.4], // Mountain View
  [-99.1, 19.4], // Mexico City
  [-47.1, -22.9], // Campinas
].map(([lon, lat]) => project(lon, lat));

/** A cell's shade: mostly dim, brighter towards the lit places; India and
 *  Karnataka in their own colours. */
function tier(x: number, y: number, row: number, col: number): 0 | 1 | 2 | 3 | 4 {
  const lonLat: [number, number] = [
    -180 + WORLD_HEX.step / 2 + col * WORLD_HEX.step + (row % 2 ? WORLD_HEX.step / 2 : 0),
    WORLD_HEX.lat0 - row * WORLD_HEX.rowStep,
  ];
  if (inside(lonLat, KARNATAKA)) return 4;
  if (inside(lonLat, INDIA)) return 3;
  const near = Math.min(...[HUB, ...NODES].map(([nx, ny]) => Math.hypot(nx - x, ny - y)));
  if (near < 16) return 2;
  const noise = ((row * 73856093) ^ (col * 19349663)) >>> 0;
  if (near < 40 || noise % 7 === 0) return 1;
  return 0;
}

const CELLS: string[] = (() => {
  const paths = ["", "", "", "", ""];
  WORLD_HEX.rows.forEach((line, row) => {
    for (let col = 0; col < line.length; col++) {
      if (line[col] !== "1") continue;
      const cx = col * W + W / 2 + (row % 2 ? W / 2 : 0);
      const cy = row * ROW_H + R;
      paths[tier(cx, cy, row, col)] += hexPath(cx, cy, CELL_R);
    }
  });
  return paths;
})();

const ARCS = NODES.map(([x, y]) => {
  const [hx, hy] = HUB;
  const lift = Math.abs(x - hx) * 0.22 + 18;
  return `M${hx.toFixed(1)} ${hy.toFixed(1)} Q${((hx + x) / 2).toFixed(1)} ${(Math.min(hy, y) - lift).toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)}`;
});

export function WorldHoneycomb({ className }: { className?: string }) {
  const id = React.useId().replace(/:/g, "");
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={`${id}-arc`} x1="0" x2="1">
          <stop offset="0" stopColor="#8fd0ff" />
          <stop offset="1" stopColor="#ffffff" />
        </linearGradient>
        <radialGradient id={`${id}-glow`}>
          <stop offset="0" stopColor="#5ec4ff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#5ec4ff" stopOpacity="0" />
        </radialGradient>
      </defs>

      <path d={CELLS[0]} fill="#8fb8e6" fillOpacity="0.4" />
      <path d={CELLS[1]} fill="#9fd2ff" fillOpacity="0.65" />
      <path d={CELLS[2]} fill="#e2f3ff" fillOpacity="0.95" />

      <circle cx={HUB[0]} cy={HUB[1]} r="95" fill={`url(#${id}-glow)`} />
      {/* India in saffron-gold, Karnataka bright within it. */}
      <path d={CELLS[3]} fill="#ffc96b" fillOpacity="0.9" />
      <path d={CELLS[4]} fill="#fff1cf" stroke="#ffb020" strokeWidth="1.2" />

      {ARCS.map((d, i) => (
        <path
          key={d}
          d={d}
          className="wm-arc"
          style={{ animationDelay: `${(i % 7) * -0.3}s` }}
          fill="none"
          stroke={`url(#${id}-arc)`}
          strokeWidth="1.2"
          strokeOpacity="0.85"
          strokeLinecap="round"
        />
      ))}

      {NODES.map(([x, y], i) => (
        <g key={`${x}-${y}`}>
          <circle className="wm-pulse" style={{ animationDelay: `${(i % 9) * 0.3}s` }} cx={x} cy={y} r="5" fill="none" stroke="#8fd0ff" strokeWidth="1.2" />
          <circle cx={x} cy={y} r="2.8" fill="#ffffff" />
        </g>
      ))}

      <circle className="wm-pulse" cx={HUB[0]} cy={HUB[1]} r="9" fill="none" stroke="#ffffff" strokeWidth="1.5" />
      <circle cx={HUB[0]} cy={HUB[1]} r="5.5" fill="#ffffff" stroke="#5ec4ff" strokeWidth="2.5" />
    </svg>
  );
}

/** A faint honeycomb over the whole panel, fading out from the centre. */
export function HoneycombBackdrop({ className }: { className?: string }) {
  const id = React.useId().replace(/:/g, "");
  const r = 18;
  const w = r * Math.sqrt(3);
  const h = r * 3;
  return (
    <svg className={className} aria-hidden="true" focusable="false">
      <defs>
        <pattern id={`${id}-hex`} width={w} height={h} patternUnits="userSpaceOnUse">
          <path
            d={`${hexPath(w / 2, r, r)}${hexPath(0, r * 2.5, r)}${hexPath(w, r * 2.5, r)}`}
            fill="none"
            stroke="#ffffff"
            strokeOpacity="0.07"
            strokeWidth="1"
          />
        </pattern>
        <radialGradient id={`${id}-fade`} cx="50%" cy="45%" r="65%">
          <stop offset="0" stopColor="#ffffff" stopOpacity="1" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0.15" />
        </radialGradient>
        <mask id={`${id}-mask`}>
          <rect width="100%" height="100%" fill={`url(#${id}-fade)`} />
        </mask>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id}-hex)`} mask={`url(#${id}-mask)`} />
    </svg>
  );
}
