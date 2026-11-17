export type AgentName =
  | "finance_qa"
  | "tax_education"
  | "portfolio"
  | "market_analysis"
  | "goal_planning"
  | "news_synthesizer";

export type Status = "ok" | "no_source" | "clarify" | "redirect" | "needs_login" | "error";

export interface Citation {
  source: string;
  title: string;
  excerpt: string;
  verified_at: string | null;
}

export interface ResponseMeta {
  retryable?: boolean;
  awaiting?: string;
  missing?: string[];
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
  agent?: AgentName;
}

export interface ChatResponse {
  thread_id: string;
  agent: string;
  status: Status;
  text: string;
  citations: Citation[];
  data: Record<string, unknown> | null;
  meta: ResponseMeta;
  disclaimer: string;
  login_url: string | null;
}

export interface AgentInfo {
  name: string;
  ready: boolean;
}

export type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; response: ChatResponse }
  | { id: string; role: "error"; text: string; retryText: string | null; retryAgent?: AgentName | null };

export type HistoryRange = "1m" | "3m" | "6m" | "1y";

export interface HistoryPoint {
  date: string;
  close: number;
}

export interface MarketHistory {
  symbol: string;
  name: string;
  range: HistoryRange;
  currency: string;
  source: string;
  as_of: string;
  points: HistoryPoint[];
  latest: number;
  change_pct: number | null;
  high: number;
  low: number;
}
