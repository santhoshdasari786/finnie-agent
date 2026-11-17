import type { ChatResponse, Message } from "../api/types";
import { isRecord } from "../format";

/** The newest reply from `agent` whose data holds an object under `key` (for example portfolio / metrics). */
export function latestWith(messages: Message[], agent: string, key: string): ChatResponse | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "assistant" && m.response.agent === agent && isRecord(m.response.data?.[key])) return m.response;
  }
  return null;
}

/** The newest reply from `agent`, whatever it said. */
export function lastFrom(messages: Message[], agent: string): ChatResponse | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m.role === "assistant" && m.response.agent === agent) return m.response;
  }
  return null;
}
