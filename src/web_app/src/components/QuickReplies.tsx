import { isRecord } from "../format";

interface Option {
  name: string;
  label: string;
}

function options(data: Record<string, unknown> | null): Option[] {
  if (!data || !Array.isArray(data.options)) return [];
  return data.options.flatMap((o: unknown) =>
    isRecord(o) && typeof o.name === "string" && /^[a-z0-9_]+$/.test(o.name) && typeof o.label === "string"
      ? [{ name: o.name, label: o.label }]
      : [],
  );
}

export function QuickReplies({ data, onSend }: { data: Record<string, unknown> | null; onSend: (text: string) => void }) {
  const list = options(data);
  if (!list.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {list.map((o) => (
        <button key={o.name} type="button" onClick={() => onSend(`connect ${o.name}`)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700">
          {o.label}
        </button>
      ))}
    </div>
  );
}
