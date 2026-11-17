import type { Message } from "./api/types";

const THREAD_KEY = "finnie.thread";
const MESSAGES_KEY = "finnie.messages";
const MAX_MESSAGES = 60;

export interface SavedSession {
  threadId: string | null;
  messages: Message[];
}

function isMessage(x: unknown): x is Message {
  const m = x as Record<string, unknown> | null;
  if (typeof m !== "object" || m === null || typeof m.id !== "string") return false;
  if (m.role === "user") return typeof m.text === "string";
  if (m.role === "assistant") {
    const r = m.response as Record<string, unknown> | null;
    return typeof r === "object" && r !== null && typeof r.text === "string" && typeof r.agent === "string" &&
      typeof r.status === "string" && Array.isArray(r.citations);
  }
  return false;
}

export function loadSession(): SavedSession {
  let threadId: string | null = null;
  let messages: Message[] = [];
  try {
    threadId = sessionStorage.getItem(THREAD_KEY);
  } catch {
    /* storage blocked */
  }
  try {
    const raw = sessionStorage.getItem(MESSAGES_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) messages = parsed.filter(isMessage);
  } catch {
    /* corrupt or blocked: start with no messages, but keep a valid thread id */
  }
  return { threadId, messages };
}

export function saveSession(threadId: string | null, messages: Message[]): void {
  try {
    if (threadId) sessionStorage.setItem(THREAD_KEY, threadId);
    else sessionStorage.removeItem(THREAD_KEY);
    const keep = messages.filter((m) => m.role !== "error").slice(-MAX_MESSAGES);
    sessionStorage.setItem(MESSAGES_KEY, JSON.stringify(keep));
  } catch {
    /* storage can be full or blocked (private mode): the chat still works, it just will not survive a reload */
  }
}

export function clearSession(): void {
  try {
    sessionStorage.removeItem(THREAD_KEY);
    sessionStorage.removeItem(MESSAGES_KEY);
  } catch {
    /* see above */
  }
}
