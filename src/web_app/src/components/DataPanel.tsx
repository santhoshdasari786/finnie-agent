import type { ReactNode } from "react";
import { inr, isNum, isRecord, money, sign, signedPct, yearsAndMonths } from "../format";

const card = "mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs sm:p-3 sm:text-sm dark:border-slate-700 dark:bg-slate-900/50";
const th = "px-1.5 py-1 text-left font-medium text-slate-500 sm:px-2 dark:text-slate-400";
const td = "px-1.5 py-1 sm:px-2";
const signColor = { up: "text-emerald-600", down: "text-red-600", flat: "text-slate-500" } as const;

const dash = "—";
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/* ------------------------------------------------------------------ goal plan */
interface Scenario {
  name: string;
  annual_rate_pct: number;
  projected: number | null;
  gap: number | null;
  required_monthly: number | null;
  years_needed: number | null;
}

const orNull = (x: unknown) => (isNum(x) ? x : null);

function parseScenarios(x: unknown): Scenario[] | null {
  if (!Array.isArray(x) || !x.length) return null;
  const out: Scenario[] = [];
  for (const s of x) {
    if (!isRecord(s) || typeof s.name !== "string" || !isNum(s.annual_rate_pct)) return null;
    out.push({
      name: s.name, annual_rate_pct: s.annual_rate_pct, projected: orNull(s.projected), gap: orNull(s.gap),
      required_monthly: orNull(s.required_monthly), years_needed: orNull(s.years_needed),
    });
  }
  return out;
}

function GoalPlan({ plan }: { plan: Record<string, unknown> }) {
  const scenarios = parseScenarios(plan.scenarios);
  if (!scenarios) return null;
  const timeMode = !isNum(plan.years);
  // Asking "can I reach X?" without a monthly amount: a projection of nothing is meaningless, show only what is needed.
  const needOnly = isNum(plan.years) && isNum(plan.target) && !(isNum(plan.monthly) && plan.monthly > 0);
  const showProjected = !needOnly && scenarios.some((s) => s.projected !== null);
  const showGap = !needOnly && scenarios.some((s) => s.gap !== null);
  const showNeed = scenarios.some((s) => s.required_monthly !== null);
  const assumed = [
    isNum(plan.target) ? `target ${inr(plan.target)}` : "",
    isNum(plan.years) ? `${plan.years} years` : "",
    isNum(plan.monthly) && plan.monthly > 0 ? `${inr(plan.monthly)} a month` : "",
    isNum(plan.start) && plan.start > 0 ? `starting from ${inr(plan.start)}` : "",
    typeof plan.risk === "string" ? `${plan.risk} risk` : "",
  ].filter(Boolean).join(" · ");
  return (
    <section aria-label="Plan details" className={card}>
      {assumed && <p className="mb-2 text-slate-600 dark:text-slate-300">{assumed}</p>}
      <table className="w-full">
        <thead>
          <tr>
            <th className={th} scope="col">Scenario</th>
            <th className={th} scope="col">Return</th>
            {showProjected && <th className={th} scope="col">Projected</th>}
            {showGap && <th className={th} scope="col">vs target</th>}
            {showNeed && <th className={th} scope="col">Needed per month</th>}
            {timeMode && <th className={th} scope="col">Time to reach</th>}
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => (
            <tr key={s.name} className="border-t border-slate-200 dark:border-slate-700">
              <td className={td}>{cap(s.name)}</td>
              <td className={td}>{s.annual_rate_pct}%</td>
              {showProjected && <td className={td}>{s.projected === null ? dash : inr(s.projected)}</td>}
              {showGap && (
                <td className={td}>
                  {s.gap === null ? dash : s.gap < 0 ? `short by ${inr(-s.gap)}` : `ahead by ${inr(s.gap)}`}
                </td>
              )}
              {showNeed && <td className={td}>{s.required_monthly === null ? dash : inr(s.required_monthly)}</td>}
              {timeMode && <td className={td}>{s.years_needed === null ? "60+ years" : yearsAndMonths(s.years_needed)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-500">Illustrative scenarios, not a promise or a forecast.</p>
    </section>
  );
}

/* ------------------------------------------------------------------ portfolio */
interface Holding {
  symbol: string;
  value: number;
  allocation_pct: number;
  pnl_pct: number | null;
  fee: number | null;
}

function parseHoldings(x: unknown): Holding[] | null {
  if (!Array.isArray(x)) return null;
  const out: Holding[] = [];
  for (const h of x) {
    if (!isRecord(h) || typeof h.symbol !== "string" || !isNum(h.value) || !isNum(h.allocation_pct)) return null;
    out.push({ symbol: h.symbol, value: h.value, allocation_pct: h.allocation_pct, pnl_pct: orNull(h.pnl_pct), fee: orNull(h.expense_ratio_pct) });
  }
  return out;
}

function Change({ value, digits }: { value: number | null; digits: number }) {
  if (value === null) return <>{dash}</>;
  const s = sign(value);
  return <span data-sign={s} className={signColor[s]}>{signedPct(value, digits)}</span>;
}

function Portfolio({ metrics, sources }: { metrics: Record<string, unknown>; sources: unknown }) {
  const holdings = parseHoldings(metrics.holdings);
  if (!holdings || !isNum(metrics.total_value)) return null;
  const classes = isRecord(metrics.by_asset_class)
    ? Object.entries(metrics.by_asset_class).filter((e): e is [string, number] => isNum(e[1]))
    : [];
  const unpriced = Array.isArray(metrics.unpriced) ? metrics.unpriced.filter((u) => typeof u === "string") : [];
  const demo = Array.isArray(sources) && sources.includes("sample");
  const showFee = holdings.some((h) => h.fee !== null);
  const feeNotKnown = Array.isArray(metrics.expense_unknown) ? metrics.expense_unknown.filter((u) => typeof u === "string") : [];
  const costs = isNum(metrics.weighted_expense_ratio_pct) && isNum(metrics.annual_fund_cost) && isNum(metrics.expense_covered_pct)
    ? { ratio: metrics.weighted_expense_ratio_pct, yearly: metrics.annual_fund_cost, covered: metrics.expense_covered_pct }
    : null;
  return (
    <section aria-label="Portfolio details" className={card}>
      <p className="mb-2 flex items-baseline justify-between gap-2">
        <span className="text-slate-500">Total value</span>
        <span className="text-lg font-semibold">{inr(metrics.total_value)}</span>
      </p>
      {demo && <p className="mb-2 text-xs text-amber-700 dark:text-amber-300">This is demo data, not your account.</p>}
      <table className="w-full">
        <thead>
          <tr>
            <th className={th} scope="col">Holding</th>
            <th className={th} scope="col">Value</th>
            <th className={th} scope="col">Share</th>
            <th className={th} scope="col">P&amp;L</th>
            {showFee && <th className={th} scope="col">Fee</th>}
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.symbol} className="border-t border-slate-200 dark:border-slate-700">
              <td className={td}>{h.symbol}</td>
              <td className={td}>{inr(h.value)}</td>
              <td className={td}>{h.allocation_pct.toFixed(1)}%</td>
              <td className={td}><Change value={h.pnl_pct} digits={1} /></td>
              {showFee && <td className={td}>{h.fee === null ? dash : `${h.fee.toFixed(2)}%`}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      {classes.length > 0 && (
        <ul aria-label="Asset classes" className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          {classes.map(([name, pct]) => (
            <li key={name}>{name.replace(/_/g, " ")} <span className="font-medium">{pct.toFixed(1)}%</span></li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-slate-600 dark:text-slate-300">
        {isNum(metrics.diversification_score) && <>Diversification {metrics.diversification_score.toFixed(2)} / 1 · </>}
        {typeof metrics.risk_assessment === "string" && <>risk profile {metrics.risk_assessment}</>}
      </p>
      {costs && (
        <p className="mt-1 text-slate-600 dark:text-slate-300">
          Fund costs: {costs.ratio.toFixed(2)}% a year on average ({inr(costs.yearly)} a year) for the {costs.covered.toFixed(1)}% of the portfolio where the ratio is known.
          {demo && <span className="text-xs text-slate-500"> Ratios on the demo portfolio are illustrative.</span>}
        </p>
      )}
      {feeNotKnown.length > 0 && <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">Expense ratio not known for: {feeNotKnown.join(", ")}</p>}
      {unpriced.length > 0 && <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">Couldn't price: {unpriced.join(", ")}</p>}
    </section>
  );
}

/* ------------------------------------------------------------------ quotes */
interface Quote {
  symbol: string;
  price: number;
  currency: string;
  change: number | null;
  source: string;
  stale: boolean;
}

function parseQuotes(x: unknown): Quote[] | null {
  if (!Array.isArray(x) || !x.length) return null;
  const out: Quote[] = [];
  for (const q of x) {
    if (!isRecord(q) || !isRecord(q.instrument) || typeof q.instrument.symbol !== "string" || !isNum(q.price)) return null;
    out.push({
      symbol: q.instrument.symbol, price: q.price, currency: typeof q.currency === "string" ? q.currency : "INR",
      change: orNull(q.change_pct), source: typeof q.source === "string" ? q.source : "", stale: q.stale === true,
    });
  }
  return out;
}

function Quotes({ quotes, missing }: { quotes: Quote[]; missing: unknown }) {
  const absent = Array.isArray(missing) ? missing.filter((m) => typeof m === "string") : [];
  return (
    <section aria-label="Price details" className={card}>
      <table className="w-full">
        <thead>
          <tr>
            <th className={th} scope="col">Symbol</th>
            <th className={th} scope="col">Price</th>
            <th className={th} scope="col">Change</th>
            <th className={th} scope="col">Source</th>
          </tr>
        </thead>
        <tbody>
          {quotes.map((q) => (
            <tr key={q.symbol} className="border-t border-slate-200 dark:border-slate-700">
              <td className={td}>{q.symbol}</td>
              <td className={td}>{money(q.price, q.currency)}</td>
              <td className={td}><Change value={q.change} digits={2} /></td>
              <td className={td}>{q.source}{q.stale && <span className="ml-1 text-amber-700"> (stale)</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {absent.length > 0 && <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">No price for: {absent.join(", ")}</p>}
    </section>
  );
}

/* ------------------------------------------------------------------ the dispatcher */
export function DataPanel({ data }: { data: Record<string, unknown> | null }): ReactNode {
  if (!data) return null;
  if (isRecord(data.plan)) return <GoalPlan plan={data.plan} />;
  if (isRecord(data.metrics)) return <Portfolio metrics={data.metrics} sources={data.sources} />;
  const quotes = parseQuotes(data.quotes);
  if (quotes) return <Quotes quotes={quotes} missing={data.missing} />;
  return null;
}
