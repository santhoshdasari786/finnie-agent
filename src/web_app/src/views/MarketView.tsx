import { useEffect, useState, type FormEvent } from "react";
import { ApiError, type Api } from "../api/client";
import type { HistoryRange, MarketHistory } from "../api/types";
import { LineChart } from "../charts/LineChart";
import { compactMoney, formatDate, price, sign, signedPct } from "../format";

const PRESETS = [
  { label: "Nifty 50", symbol: "NIFTY50" }, { label: "Sensex", symbol: "SENSEX" }, { label: "RELIANCE", symbol: "RELIANCE" },
  { label: "TCS", symbol: "TCS" }, { label: "INFY", symbol: "INFY" }, { label: "HDFCBANK", symbol: "HDFCBANK" },
];
const RANGES: { label: string; value: HistoryRange; words: string }[] = [
  { label: "1M", value: "1m", words: "1 month" }, { label: "3M", value: "3m", words: "3 months" },
  { label: "6M", value: "6m", words: "6 months" }, { label: "1Y", value: "1y", words: "1 year" },
];
const SYMBOL = /^[A-Z0-9&-]{1,20}$/;
const ALIASES: Record<string, string> = { NIFTY: "NIFTY50" };
const tone = { up: "text-emerald-600", down: "text-red-600", flat: "text-slate-500" } as const;
const card = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800";
const chip = "rounded-full border px-3 py-1 text-sm font-medium";

type State =
  | { kind: "loading" }
  | { kind: "ready"; data: MarketHistory }
  | { kind: "error"; message: string; retryable: boolean };

export function MarketView({ api }: { api: Api }) {
  const [symbol, setSymbol] = useState("NIFTY50");
  const [range, setRange] = useState<HistoryRange>("3m");
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<State>({ kind: "loading" });
  const [typed, setTyped] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;                                   // a slow answer for an earlier choice must not overwrite a newer one
    setState({ kind: "loading" });
    api.marketHistory(symbol, range).then(
      (data) => current && setState({ kind: "ready", data }),
      (e: unknown) => {
        if (!current) return;
        const known = e instanceof ApiError ? e : null;
        setState({ kind: "error", message: known ? known.message : "Something went wrong. Please try again.", retryable: known ? known.retryable : true });
      },
    );
    return () => {
      current = false;
    };
  }, [api, symbol, range, attempt]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = typed.trim().toUpperCase();
    if (!text) return;
    if (!SYMBOL.test(text)) {
      setFormError("Use a ticker such as TCS, or Nifty or Sensex.");
      return;
    }
    setFormError(null);
    setTyped("");
    setSymbol(ALIASES[text] ?? text);
  }

  return (
    <section aria-labelledby="market-heading" className="space-y-4">
      <h2 id="market-heading" className="sr-only">Market</h2>
      <div className="flex flex-wrap items-center gap-2">
        {PRESETS.map((p) => (
          <button key={p.symbol} type="button" aria-pressed={symbol === p.symbol} onClick={() => setSymbol(p.symbol)}
                  className={`${chip} ${symbol === p.symbol ? "border-indigo-600 bg-indigo-600 text-white" : "border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"}`}>
            {p.label}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor="market-symbol" className="block text-sm font-medium">Symbol</label>
          <input id="market-symbol" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" placeholder="e.g. WIPRO"
                 className="mt-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-900" />
        </div>
        <button type="submit" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800">Show</button>
        <div className="ml-auto flex gap-1">
          {RANGES.map((r) => (
            <button key={r.value} type="button" aria-pressed={range === r.value} onClick={() => setRange(r.value)}
                    className={`rounded-md border px-2.5 py-1 text-sm ${range === r.value ? "border-indigo-600 bg-indigo-50 font-semibold text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300" : "border-slate-300 dark:border-slate-600"}`}>
              {r.label}
            </button>
          ))}
        </div>
      </form>
      {formError && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{formError}</p>}

      {state.kind === "loading" && <p role="status" className="text-sm text-slate-500 dark:text-slate-400">Loading prices…</p>}
      {state.kind === "error" && (
        <div role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
          <p>{state.message}</p>
          {state.retryable && (
            <button type="button" onClick={() => setAttempt((a) => a + 1)}
                    className="mt-2 rounded-md border border-red-400 px-3 py-1 font-medium hover:bg-red-100 dark:hover:bg-red-900/40">
              Try again
            </button>
          )}
        </div>
      )}
      {state.kind === "ready" && <Ready data={state.data} />}
    </section>
  );
}

function Ready({ data }: { data: MarketHistory }) {
  const words = RANGES.find((r) => r.value === data.range)?.words ?? data.range;     // what the data covers, not which button was last pressed
  const first = data.points[0];
  const last = data.points[data.points.length - 1];
  const change = data.change_pct;
  return (
    <div className={`${card} space-y-4`}>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h2 className="text-xl font-semibold">{data.name}</h2>
        <p data-testid="latest" className="text-2xl font-semibold">{price(data.latest, data.currency)}</p>
        <p data-testid="change" className="text-sm">
          {change === null ? <span>—</span> : <span data-sign={sign(change)} className={`font-medium ${tone[sign(change)]}`}>{signedPct(change, 2)}</span>}{" "}
          <span className="text-slate-500 dark:text-slate-400">over {words}</span>
        </p>
      </div>
      <LineChart
        series={[{ name: data.name, tone: change === null ? "neutral" : change >= 0 ? "up" : "down", points: data.points.map((p, i) => ({ x: i, y: p.close })) }]}
        ariaLabel={`${data.name} closing price, last ${words}: from ${price(first.close, data.currency)} on ${formatDate(first.date)} to ${price(last.close, data.currency)} on ${formatDate(last.date)}`}
        formatY={(n) => compactMoney(n, data.currency)}
        formatX={(i) => formatDate(data.points[Math.min(data.points.length - 1, Math.max(0, Math.round(i)))].date)}
      />
      <dl className="flex gap-6 text-sm">
        <div><dt className="text-slate-500 dark:text-slate-400">High</dt><dd className="font-medium">{price(data.high, data.currency)}</dd></div>
        <div><dt className="text-slate-500 dark:text-slate-400">Low</dt><dd className="font-medium">{price(data.low, data.currency)}</dd></div>
      </dl>
      <p className="text-xs text-slate-500 dark:text-slate-400">Source: {data.source} · {formatDate(data.as_of)}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400">Prices can be delayed. For education only, not financial advice.</p>
    </div>
  );
}
