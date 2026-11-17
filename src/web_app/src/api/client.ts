import type { AgentInfo, ChatRequest, ChatResponse, HistoryRange, MarketHistory } from "./types";

export class ApiError extends Error {
  readonly status?: number;
  readonly retryable: boolean;

  constructor(message: string, status?: number, retryable = true) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryable = retryable;
  }
}

export interface Api {
  chat(req: ChatRequest): Promise<ChatResponse>;
  agents(): Promise<AgentInfo[]>;
  endSession(threadId: string): Promise<void>;
  marketHistory(symbol: string, range: HistoryRange): Promise<MarketHistory>;
}

const DEFAULT_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function looksLikeChatResponse(x: unknown): x is ChatResponse {
  const r = x as Record<string, unknown> | null;
  return (
    typeof r === "object" && r !== null &&
    typeof r.thread_id === "string" && typeof r.agent === "string" && typeof r.status === "string" &&
    typeof r.text === "string" && typeof r.disclaimer === "string" && Array.isArray(r.citations)
  );
}

const isStr = (x: unknown) => typeof x === "string";
const isNum = (x: unknown) => typeof x === "number" && Number.isFinite(x);

function looksLikeHistory(x: unknown): x is MarketHistory {
  const r = x as Record<string, unknown> | null;
  if (typeof r !== "object" || r === null) return false;
  const points = r.points;
  return (
    isStr(r.symbol) && isStr(r.name) && isStr(r.range) && isStr(r.currency) && isStr(r.source) && isStr(r.as_of) &&
    isNum(r.latest) && isNum(r.high) && isNum(r.low) && (r.change_pct === null || isNum(r.change_pct)) &&
    Array.isArray(points) &&
    points.every((p) => typeof p === "object" && p !== null && isStr((p as Record<string, unknown>).date) && isNum((p as Record<string, unknown>).close))
  );
}


async function toError(res: Response): Promise<ApiError> {
  const generic = `The server returned an error (${res.status}).`;
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    return new ApiError(generic, res.status, res.status >= 500);
  }
  const b = body as { error?: unknown; detail?: unknown };
  if (res.status === 422) {
    const first = Array.isArray(b.detail) ? (b.detail[0] as { msg?: unknown } | undefined) : undefined;
    const msg = typeof first?.msg === "string" ? first.msg : typeof b.detail === "string" ? b.detail : generic;
    return new ApiError(msg.replace(/^Value error, /, ""), 422, false);
  }
  return new ApiError(typeof b.error === "string" ? b.error : generic, res.status, res.status >= 500);
}

export function createApi(
  baseUrl: string = DEFAULT_BASE,
  fetchImpl: typeof fetch = (...args) => fetch(...args),
  timeoutMs = 60_000,
): Api {
  const base = baseUrl.replace(/\/+$/, "");

  async function request(path: string, init: RequestInit = {}): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let res: Response;
    try {
      res = await fetchImpl(`${base}${path}`, { ...init, signal: controller.signal });
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        throw new ApiError("The server is taking too long to answer. Please try again.");
      }
      throw new ApiError(`I can't reach the server at ${base}. Is it running?`);
    } finally {
      clearTimeout(timer);
    }
    if (!res.ok) throw await toError(res);
    return res;
  }

  return {
    async chat(req) {
      const res = await request("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      const body: unknown = await res.json();
      if (!looksLikeChatResponse(body)) throw new ApiError("The server sent an unexpected reply.");
      return body;
    },
    async agents() {
      return (await (await request("/agents")).json()) as AgentInfo[];
    },
    async marketHistory(symbol, range) {
      const res = await request(`/market/history?symbol=${encodeURIComponent(symbol)}&range=${range}`);
      let body: unknown;
      try {
        body = await res.json();
      } catch {
        throw new ApiError("The server sent an unexpected reply.");
      }
      if (!looksLikeHistory(body)) throw new ApiError("The server sent an unexpected reply.");
      return body;
    },

    async endSession(threadId) {
      await request(`/sessions/${encodeURIComponent(threadId)}`, { method: "DELETE" });
    },
  };
}

export const api: Api = createApi();
