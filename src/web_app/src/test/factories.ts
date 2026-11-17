import type { ChatResponse, HistoryRange, MarketHistory, Message } from "../api/types";

export function makeResponse(over: Partial<ChatResponse> = {}): ChatResponse {
  return {
    thread_id: "thread-0001",
    agent: "finance_qa",
    status: "ok",
    text: "A SIP invests a fixed amount regularly.",
    citations: [],
    data: null,
    meta: {},
    disclaimer: "Educational information only, not financial advice.",
    login_url: null,
    ...over,
  };
}

export function assistant(over: Partial<ChatResponse> = {}, id = "a1"): Message {
  return { id, role: "assistant", response: makeResponse(over) };
}

export function user(text: string, id = "u1"): Message {
  return { id, role: "user", text };
}

/** A fetch that answers from a queue of canned responses and records every call. */
export function fakeFetch(...replies: Array<{ status?: number; body?: unknown; raw?: string } | Error>) {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  const impl = (async (url: string | URL | Request, init: RequestInit = {}) => {
    calls.push({ url: String(url), init });
    const next = replies[Math.min(calls.length - 1, replies.length - 1)];
    if (next instanceof Error) throw next;
    const status = next.status ?? 200;
    const text = next.raw ?? (next.body === undefined ? "" : JSON.stringify(next.body));
    return new Response(status === 204 ? null : text, { status, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  return { fetch: impl, calls };
}

export function makeHistory(over: Partial<MarketHistory> = {}): MarketHistory {
  const closes = [100, 104, 102, 110];
  return {
    symbol: "TCS", name: "TCS", range: "3m" as HistoryRange, currency: "INR", source: "yfinance",
    as_of: "2026-11-17T05:30:00+00:00",
    points: closes.map((close, i) => ({ date: `2026-08-${String(3 + i).padStart(2, "0")}`, close })),
    latest: 110, change_pct: 10, high: 110, low: 100, stale: false, age_seconds: 600,
    ...over,
  };
}

export function portfolioData(over: Record<string, unknown> = {}) {
  return {
    metrics: {
      total_value: 1_000_000,
      holdings: [
        { symbol: "TCS", quantity: 10, price: 3000, value: 300_000, allocation_pct: 30, pnl_pct: 12.5 },
        { symbol: "INFY", quantity: 20, price: 1500, value: 300_000, allocation_pct: 30, pnl_pct: -3.2 },
        { symbol: "GOLDBEES", quantity: 100, price: 400, value: 400_000, allocation_pct: 40, pnl_pct: null },
      ],
      by_asset_class: { equity: 60, gold: 40 },
      top_holding_pct: 40,
      diversification_score: 0.66,
      risk_assessment: "moderate",
      unpriced: [], unclassified: [],
      ...over,
    },
    sources: ["sample"],
  };
}

export function goalData(over: Record<string, unknown> = {}) {
  const path = (name: string, rate: number, end: number) => ({
    name, annual_rate_pct: rate,
    points: [0, 5, 10].map((year) => ({ year, value: Math.round((end * year) / 10) })),
  });
  return {
    plan: {
      years: 10, monthly: 20000, start: 0, target: 5_000_000, risk: "moderate", already_met: false,
      scenarios: [
        { name: "pessimistic", annual_rate_pct: 3, projected: 2_794_828, gap: -2_205_172, required_monthly: 71561, years_needed: null },
        { name: "expected", annual_rate_pct: 7, projected: 3_461_696, gap: -1_538_304, required_monthly: 57775, years_needed: null },
        { name: "optimistic", annual_rate_pct: 11, projected: 5_339_963, gap: 339_963, required_monthly: 46083, years_needed: null },
      ],
    },
    paths: [path("pessimistic", 3, 2_794_828), path("expected", 7, 3_461_696), path("optimistic", 11, 5_339_963)],
    ...over,
  };
}
