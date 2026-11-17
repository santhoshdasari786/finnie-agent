import { donutSlices } from "./geometry";

const SIZE = 120;
const RADIUS = 44;
const STROKE = 18;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

// Whole class names, so Tailwind can see them.
const PALETTE = [
  { stroke: "stroke-indigo-500", bg: "bg-indigo-500" },
  { stroke: "stroke-emerald-500", bg: "bg-emerald-500" },
  { stroke: "stroke-amber-500", bg: "bg-amber-500" },
  { stroke: "stroke-sky-500", bg: "bg-sky-500" },
  { stroke: "stroke-rose-500", bg: "bg-rose-500" },
  { stroke: "stroke-violet-500", bg: "bg-violet-500" },
  { stroke: "stroke-teal-500", bg: "bg-teal-500" },
  { stroke: "stroke-orange-500", bg: "bg-orange-500" },
];

interface Props {
  title: string;
  slices: { label: string; value: number }[];
  center?: string;
}

export function DonutChart({ title, slices, center }: Props) {
  const clean = slices
    .filter((s) => Number.isFinite(s.value) && s.value > 0)
    .map((s) => ({ label: s.label.replace(/_/g, " "), value: s.value }));
  if (!clean.length) return <p className="text-sm text-slate-500 dark:text-slate-400">No data to chart.</p>;

  const arcs = donutSlices(clean.map((s) => s.value));
  const pct = (i: number) => `${(arcs[i].fraction * 100).toFixed(1)}%`;
  const name = `${title}: ${clean.map((s, i) => `${s.label} ${pct(i)}`).join(", ")}`;

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="relative size-32 shrink-0">
        <svg role="img" aria-label={name} viewBox={`0 0 ${SIZE} ${SIZE}`} className="size-full -rotate-90">
          <circle cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" strokeWidth={STROKE}
                  className="stroke-slate-200 dark:stroke-slate-700" aria-hidden="true" />
          {clean.map((s, i) => (
            <circle
              key={s.label} data-slice={s.label} data-fraction={String(arcs[i].fraction)}
              cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" strokeWidth={STROKE}
              className={PALETTE[i % PALETTE.length].stroke}
              strokeDasharray={`${arcs[i].fraction * CIRCUMFERENCE} ${CIRCUMFERENCE}`}
              strokeDashoffset={String(-arcs[i].offset * CIRCUMFERENCE)}
            />
          ))}
        </svg>
        {center && <span className="absolute inset-0 grid place-items-center text-sm font-semibold">{center}</span>}
      </div>
      <ul aria-label={`${title} legend`} className="space-y-1 text-sm">
        {clean.map((s, i) => (
          <li key={s.label} className="flex items-center gap-2">
            <span aria-hidden="true" className={`size-2.5 rounded-full ${PALETTE[i % PALETTE.length].bg}`} />
            <span className="capitalize">{s.label}</span>{" "}
            <span className="font-medium">{pct(i)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
