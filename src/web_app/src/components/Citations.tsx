import type { Citation } from "../api/types";

const isWeb = (s: string) => /^https?:\/\//i.test(s);
const chip = "rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200";

export function Citations({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <ul aria-label="Sources" className="mt-3 flex flex-wrap gap-2">
      {citations.map((c, i) => {
        const hint = [c.excerpt, c.verified_at ? `verified ${c.verified_at}` : ""].filter(Boolean).join(" · ");
        return (
          <li key={i}>
            {isWeb(c.source) ? (
              <a href={c.source} target="_blank" rel="noopener noreferrer" title={hint}
                 className={`${chip} inline-block hover:bg-slate-100 dark:hover:bg-slate-700`}>
                [{i + 1}] {c.title}
              </a>
            ) : (
              <span title={hint} className={`${chip} inline-block`}>
                [{i + 1}] {c.title}
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
