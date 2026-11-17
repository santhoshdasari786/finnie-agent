import type { ChatResponse, Message } from "../api/types";

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
