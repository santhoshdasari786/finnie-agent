export const AGENT_LABELS: Record<string, string> = {
  finance_qa: "Q&A",
  tax_education: "Tax",
  portfolio: "Portfolio",
  market_analysis: "Market",
  goal_planning: "Goals",
  news_synthesizer: "News",
  guard: "Safety",
  router: "Assistant",
};

const COLORS: Record<string, string> = {
  finance_qa: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200",
  tax_education: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
  portfolio: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
  market_analysis: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200",
  goal_planning: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200",
  news_synthesizer: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200",
  guard: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
};
const FALLBACK = "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200";

export function AgentBadge({ agent }: { agent: string }) {
  return (
    <span
      data-agent={agent}
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${COLORS[agent] ?? FALLBACK}`}
    >
      {AGENT_LABELS[agent] ?? agent}
    </span>
  );
}
