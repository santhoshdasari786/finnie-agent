import { useState, type FormEvent } from "react";
import type { AgentName, ChatResponse, Message } from "../api/types";
import { LineChart, type Series } from "../charts/LineChart";
import { DataPanel } from "../components/DataPanel";
import { RichText } from "../components/RichText";
import { compactMoney, inr, isNum, isRecord } from "../format";
import { buildGoalQuestion, problems, type Field, type GoalForm, type Problem } from "../lib/goalQuestion";
import { lastFrom } from "../lib/latest";

interface Props {
  messages: Message[];
  pending: boolean;
  onSend: (text: string, agent?: AgentName) => Promise<ChatResponse | null>;
}

const EMPTY: GoalForm = { years: "", target: "", monthly: "", start: "", risk: "", rate: "" };
const card = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800";
const input = "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900";
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

const FIELDS: { name: Exclude<Field, "risk">; label: string }[] = [
  { name: "years", label: "Years to goal" },
  { name: "target", label: "Target amount (₹)" },
  { name: "monthly", label: "Monthly saving (₹)" },
  { name: "start", label: "Starting balance (₹)" },
  { name: "rate", label: "Assumed yearly return (%)" },
];

function seriesFrom(paths: unknown): Series[] {
  if (!Array.isArray(paths)) return [];
  const out: Series[] = [];
  for (const p of paths) {
    if (!isRecord(p) || typeof p.name !== "string" || !isNum(p.annual_rate_pct) || !Array.isArray(p.points)) continue;
    const points = p.points.filter((q) => isRecord(q) && isNum(q.year) && isNum(q.value)).map((q) => ({ x: (q as { year: number }).year, y: (q as { value: number }).value }));
    out.push({ name: `${cap(p.name)} ${p.annual_rate_pct}%`, points });
  }
  return out;
}

export function GoalsView({ messages, pending, onSend }: Props) {
  const [form, setForm] = useState<GoalForm>(EMPTY);
  const [found, setFound] = useState<Problem[]>([]);
  const result = lastFrom(messages, "goal_planning");
  const plan = isRecord(result?.data?.plan) ? result.data.plan : null;
  const series = result ? seriesFrom(result.data?.paths) : [];

  const set = (field: Field, value: string) => setForm((f) => ({ ...f, [field]: value }));

  function submit(e: FormEvent) {
    e.preventDefault();
    const issues = problems(form);
    setFound(issues);
    if (issues.length) return;
    void onSend(buildGoalQuestion(form), "goal_planning");
  }

  return (
    <section aria-labelledby="goals-heading" className="space-y-4">
      <h2 id="goals-heading" className="text-xl font-semibold">Goal planner</h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <form onSubmit={submit} noValidate className={`${card} space-y-3`}>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Amounts are in rupees. You can type commas, like 50,00,000. Leave the years empty to find out how long it takes.
          </p>
          {FIELDS.map(({ name, label }) => (
            <div key={name}>
              <label htmlFor={`goal-${name}`} className="text-sm font-medium">{label}</label>
              <input id={`goal-${name}`} type="text" inputMode="decimal" autoComplete="off" value={form[name]}
                     aria-invalid={found.some((p) => p.field === name) || undefined}
                     onChange={(e) => set(name, e.target.value)} className={input} />
            </div>
          ))}
          <div>
            <label htmlFor="goal-risk" className="text-sm font-medium">Risk appetite</label>
            <select id="goal-risk" value={form.risk} onChange={(e) => set("risk", e.target.value)} className={input}>
              <option value="">Not sure</option>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          {found.length > 0 && (
            <div role="alert" className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
              <ul className="list-disc pl-4">{found.map((p) => <li key={p.message}>{p.message}</li>)}</ul>
            </div>
          )}
          <div className="flex gap-2">
            <button type="submit" disabled={pending}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
              Plan my goal
            </button>
            <button type="button" onClick={() => { setForm(EMPTY); setFound([]); }}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-700">
              Clear
            </button>
          </div>
          {pending && <p role="status" className="text-sm text-slate-500 dark:text-slate-400">Working on it…</p>}
        </form>

        <div className="space-y-4">
          {result?.status === "error" && (
            <div role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
              {result.text}
            </div>
          )}
          {result && result.status !== "error" && (
            <>
              {series.length > 0 && (
                <div className={card}>
                  <LineChart
                    series={series}
                    ariaLabel={`Projected balance by year${isNum(plan?.years) ? ` over ${plan.years} years` : ""}`}
                    formatY={(n) => compactMoney(n, "INR")}
                    formatX={(x) => `Year ${x}`}
                    refLine={isNum(plan?.target) ? { y: plan.target, label: `Target ${inr(plan.target)}` } : undefined}
                  />
                </div>
              )}
              <div className={card}>
                <RichText text={result.text} />
                <DataPanel data={result.data} />
                <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{result.disclaimer}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
