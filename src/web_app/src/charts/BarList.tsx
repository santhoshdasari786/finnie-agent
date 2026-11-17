interface Props {
  title: string;
  items: { label: string; value: number }[];
  max?: number;
  format?: (value: number) => string;
}

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, n));

export function BarList({ title, items, max = 100, format = (v) => `${v.toFixed(1)}%` }: Props) {
  const clean = items.filter((i) => Number.isFinite(i.value));
  if (!clean.length) return <p className="text-sm text-slate-500 dark:text-slate-400">No data to chart.</p>;
  return (
    <ul aria-label={title} className="space-y-2 text-sm">
      {clean.map((item) => {
        const width = Math.round(clamp((item.value / max) * 100, 0, 100) * 100) / 100;
        return (
          <li key={item.label}>
            <div className="flex justify-between gap-2">
              <span className="truncate">{item.label}</span>
              <span className="font-medium">{format(item.value)}</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-slate-200 dark:bg-slate-700">
              <div data-bar className="h-2 rounded-full bg-indigo-500" style={{ width: `${width}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
