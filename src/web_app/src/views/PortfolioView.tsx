import type { AgentName, ChatResponse, Message } from "../api/types";
import { BarList } from "../charts/BarList";
import { DonutChart } from "../charts/DonutChart";
import { DataPanel } from "../components/DataPanel";
import { LoginPrompt } from "../components/LoginPrompt";
import { RichText } from "../components/RichText";
import { compactMoney, isNum, isRecord } from "../format";
import { lastFrom, latestWith } from "../lib/latest";

interface Props {
  messages: Message[];
  pending: boolean;
  onSend: (text: string, agent?: AgentName) => Promise<ChatResponse | null>;
}

const button = "rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50";
const card = "rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800";

function read(data: Record<string, unknown> | null) {
  const metrics = isRecord(data?.metrics) ? data.metrics : {};
  const holdings = (Array.isArray(metrics.holdings) ? metrics.holdings : [])
    .filter((h): h is Record<string, unknown> => isRecord(h) && typeof h.symbol === "string" && isNum(h.allocation_pct))
    .map((h) => ({ label: h.symbol as string, value: h.allocation_pct as number }))
    .sort((a, b) => b.value - a.value)                                   // stable: ties keep their order
    .slice(0, 10);
  const classes = Object.entries(isRecord(metrics.by_asset_class) ? metrics.by_asset_class : {})
    .filter((e): e is [string, number] => isNum(e[1]))
    .map(([label, value]) => ({ label, value }));
  return {
    holdings, classes,
    total: isNum(metrics.total_value) ? metrics.total_value : null,
    count: Array.isArray(metrics.holdings) ? metrics.holdings.length : null,
    diversification: isNum(metrics.diversification_score) ? metrics.diversification_score : null,
    top: isNum(metrics.top_holding_pct) ? metrics.top_holding_pct : null,
    fee: isNum(metrics.weighted_expense_ratio_pct) ? metrics.weighted_expense_ratio_pct : null,
    risk: typeof metrics.risk_assessment === "string" ? metrics.risk_assessment : null,
  };
}

export function PortfolioView({ messages, pending, onSend }: Props) {
  const analysis = latestWith(messages, "portfolio", "metrics");
  const last = lastFrom(messages, "portfolio");
  const needsLogin = last?.status === "needs_login" && last.login_url ? last.login_url : null;
  const problem = last?.status === "error" ? last : null;

  async function connectAndAnalyze(source: "sample" | "kite") {
    const connected = await onSend(`connect ${source}`, "portfolio");
    if (connected?.status === "ok") await onSend("analyze my portfolio", "portfolio");
  }

  const view = analysis ? read(analysis.data) : null;
  const tiles = view && [
    ["Diversification", view.diversification === null ? null : `${view.diversification.toFixed(2)} / 1`],
    ["Risk profile", view.risk ? view.risk.charAt(0).toUpperCase() + view.risk.slice(1) : null],
    ["Largest holding", view.top === null ? null : `${view.top.toFixed(1)}%`],
    ["Fund costs", view.fee === null ? null : `${view.fee.toFixed(2)}% a year`],
    ["Holdings", view.count === null ? null : String(view.count)],
  ].filter((t): t is [string, string] => t[1] !== null);

  return (
    <section aria-labelledby="portfolio-heading" className="space-y-4">
      <h2 id="portfolio-heading" className="text-xl font-semibold">Portfolio</h2>
      {pending && <p role="status" className="text-sm text-slate-500 dark:text-slate-400">Working on it…</p>}
      {problem && (
        <div role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
          {problem.text}
        </div>
      )}

      {!analysis && (
        <div className={card}>
          <p className="text-slate-600 dark:text-slate-300">
            See how your money is spread out: allocation, diversification and a risk profile. Start with the demo portfolio, or connect your Zerodha account (read-only, no orders can be placed).
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" disabled={pending} onClick={() => connectAndAnalyze("sample")}
                    className={`${button} bg-indigo-600 text-white hover:bg-indigo-700`}>
              Analyze the sample portfolio
            </button>
            <button type="button" disabled={pending} onClick={() => connectAndAnalyze("kite")}
                    className={`${button} border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-700`}>
              Connect Zerodha (read-only)
            </button>
          </div>
        </div>
      )}

      {needsLogin && (
        <LoginPrompt url={needsLogin} onSend={(text) => { void (text === "connect kite" ? connectAndAnalyze("kite") : onSend(text, "portfolio")); }} />
      )}

      {analysis && view && tiles && (
        <>
          {tiles.length > 0 && (
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {tiles.map(([label, value]) => (
                <div key={label} className={card}>
                  <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
                  <dd className="mt-1 text-lg font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {view.classes.length > 0 && (
              <div className={card}>
                <h3 className="mb-3 text-sm font-medium">Asset classes</h3>
                <DonutChart title="Allocation by asset class" slices={view.classes}
                            center={view.total === null ? undefined : compactMoney(view.total, "INR")} />
              </div>
            )}
            {view.holdings.length > 0 && (
              <div className={card}>
                <h3 className="mb-3 text-sm font-medium">Holdings</h3>
                <BarList title="Holdings by share" items={view.holdings} />
              </div>
            )}
          </div>
          <div className={card}>
            <RichText text={analysis.text} />
            <DataPanel data={analysis.data} />
            <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{analysis.disclaimer}</p>
          </div>
          <button type="button" disabled={pending} onClick={() => void onSend("analyze my portfolio", "portfolio")}
                  className={`${button} border border-slate-300 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-700`}>
            Refresh analysis
          </button>
        </>
      )}
    </section>
  );
}
