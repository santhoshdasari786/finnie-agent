import { extent, linePath, padDomain, scaleLinear, type Box } from "./geometry";

export interface Series {
  name: string;
  points: { x: number; y: number }[];
  tone?: "up" | "down" | "neutral";
}

interface Props {
  series: Series[];
  ariaLabel: string;
  formatY: (value: number) => string;
  formatX?: (value: number) => string;
  refLine?: { y: number; label: string };
}

const BOX: Box = { width: 640, height: 260, left: 64, right: 16, top: 16, bottom: 32 };

// Whole class names, so Tailwind can see them.
const PALETTE = [
  { stroke: "stroke-indigo-500", bg: "bg-indigo-500" },
  { stroke: "stroke-amber-500", bg: "bg-amber-500" },
  { stroke: "stroke-emerald-500", bg: "bg-emerald-500" },
  { stroke: "stroke-rose-500", bg: "bg-rose-500" },
];
const TONES = {
  up: { stroke: "stroke-emerald-600", bg: "bg-emerald-600" },
  down: { stroke: "stroke-red-600", bg: "bg-red-600" },
};

export function LineChart({ series, ariaLabel, formatY, formatX = String, refLine }: Props) {
  const drawn = series
    .map((s) => ({ ...s, points: s.points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y)) }))
    .filter((s) => s.points.length >= 2);
  if (!drawn.length) return <p className="text-sm text-slate-500 dark:text-slate-400">Not enough data to draw a chart.</p>;

  const xDomain = extent(drawn.flatMap((s) => s.points.map((p) => p.x)));
  const yValues = drawn.flatMap((s) => s.points.map((p) => p.y));
  if (refLine) yValues.push(refLine.y);
  const yDomain = padDomain(extent(yValues));
  const sy = scaleLinear(yDomain, [BOX.height - BOX.bottom, BOX.top]);
  const ticks = [yDomain[1], (yDomain[0] + yDomain[1]) / 2, yDomain[0]];
  const colours = (s: Series, i: number) => (s.tone && s.tone !== "neutral" ? TONES[s.tone] : PALETTE[i % PALETTE.length]);

  return (
    <div>
      <svg role="img" aria-label={ariaLabel} viewBox={`0 0 ${BOX.width} ${BOX.height}`} className="h-auto w-full">
        {ticks.map((t) => (
          <line key={t} x1={BOX.left} x2={BOX.width - BOX.right} y1={sy(t)} y2={sy(t)}
                className="stroke-slate-200 dark:stroke-slate-700" strokeWidth={1} />
        ))}
        <g data-testid="y-axis" className="fill-slate-500 text-[11px] dark:fill-slate-400">
          {ticks.map((t) => (
            <text key={t} x={BOX.left - 8} y={sy(t) + 4} textAnchor="end">{formatY(t)}</text>
          ))}
        </g>
        <g data-testid="x-axis" className="fill-slate-500 text-[11px] dark:fill-slate-400">
          <text x={BOX.left} y={BOX.height - 10} textAnchor="start">{formatX(xDomain[0])}</text>
          <text x={BOX.width - BOX.right} y={BOX.height - 10} textAnchor="end">{formatX(xDomain[1])}</text>
        </g>
        {refLine && (
          <>
            <line data-testid="ref-line" x1={BOX.left} x2={BOX.width - BOX.right} y1={sy(refLine.y)} y2={sy(refLine.y)}
                  className="stroke-slate-500" strokeWidth={1.5} strokeDasharray="6 4" />
            <text x={BOX.width - BOX.right} y={sy(refLine.y) - 6} textAnchor="end" className="fill-slate-600 text-[11px] dark:fill-slate-300">
              {refLine.label}
            </text>
          </>
        )}
        {drawn.map((s, i) => (
          <path key={s.name} data-series={s.name} d={linePath(s.points, xDomain, yDomain, BOX)} fill="none" strokeWidth={2.5}
                strokeLinejoin="round" strokeLinecap="round" className={colours(s, i).stroke} />
        ))}
      </svg>
      {drawn.length > 1 && (
        <ul aria-label="Legend" className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {drawn.map((s, i) => (
            <li key={s.name} className="flex items-center gap-1.5">
              <span aria-hidden="true" className={`size-2.5 rounded-full ${colours(s, i).bg}`} />{s.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
