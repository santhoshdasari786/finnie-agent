import { useEffect, useRef, type KeyboardEvent } from "react";

export const tabId = (id: string) => `tab-${id}`;
export const panelId = (id: string) => `panel-${id}`;

interface Props<T extends string> {
  tabs: { id: T; label: string }[];
  active: T;
  onChange: (id: T) => void;
}

export function Tabs<T extends string>({ tabs, active, onChange }: Props<T>) {
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});
  const focusAfterChange = useRef<T | null>(null);

  useEffect(() => {
    if (focusAfterChange.current === active) {
      buttons.current[active]?.focus();
      focusAfterChange.current = null;
    }
  }, [active]);

  function onKeyDown(e: KeyboardEvent, index: number) {
    const last = tabs.length - 1;
    const target =
      e.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : e.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : e.key === "Home" ? 0
      : e.key === "End" ? last
      : null;
    if (target === null) return;
    e.preventDefault();
    focusAfterChange.current = tabs[target].id;
    onChange(tabs[target].id);
  }

  return (
    <div role="tablist" aria-label="Sections" className="flex gap-1">
      {tabs.map((t, i) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id} ref={(el) => { buttons.current[t.id] = el; }} type="button" role="tab" id={tabId(t.id)}
            aria-selected={selected} aria-controls={panelId(t.id)} tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.id)} onKeyDown={(e) => onKeyDown(e, i)}
            className={`rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium ${selected
              ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
              : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"}`}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
