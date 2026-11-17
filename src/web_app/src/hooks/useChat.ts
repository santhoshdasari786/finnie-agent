import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api as defaultApi, type Api } from "../api/client";
import type { AgentName, ChatResponse, Message } from "../api/types";
import { loadSession, saveSession, type SavedSession } from "../session";

let counter = 0;
const nextId = () => `m${Date.now().toString(36)}-${counter++}`;

export function useChat(api: Api = defaultApi) {
  const saved = useRef<SavedSession | null>(null);
  saved.current ??= loadSession();
  const [messages, setMessages] = useState<Message[]>(saved.current.messages);
  const [pending, setPending] = useState(false);
  const threadId = useRef<string | null>(saved.current.threadId);
  const busy = useRef(false);

  useEffect(() => {
    saveSession(threadId.current, messages);
  }, [messages]);

  const run = useCallback(
    async (text: string, addUserMessage: boolean, agent?: AgentName): Promise<ChatResponse | null> => {
      if (busy.current) return null;
      busy.current = true;
      setPending(true);
      if (addUserMessage) setMessages((m) => [...m, { id: nextId(), role: "user", text }]);
      try {
                const res = await api.chat({
          message: text,
          ...(threadId.current ? { thread_id: threadId.current } : {}),
          ...(agent ? { agent } : {}),
        });
        threadId.current = res.thread_id;
        setMessages((m) => [...m, { id: nextId(), role: "assistant", response: res }]);
        return res;
      } catch (e) {
        const known = e instanceof ApiError ? e : null;
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "error",
            text: known ? known.message : "Something went wrong. Please try again.",
            retryText: known && !known.retryable ? null : text,
            retryAgent: agent ?? null, 
          },
        ]);
        return null;
      } finally {
        busy.current = false;
        setPending(false);
      }
    },
    [api],
  );

  const send = useCallback(
    async (raw: string, agent?: AgentName): Promise<ChatResponse | null> => {
      const text = raw.trim();
      return text ? run(text, true, agent) : null;
    },
    [run],
  );

  const retry = useCallback(async () => {
    const failed = [...messages].reverse().find((m) => m.role === "error");
    if (!failed || failed.role !== "error" || !failed.retryText) return;
    setMessages((m) => m.filter((x) => x.id !== failed.id));
    await run(failed.retryText, false, failed.retryAgent ?? undefined);
  }, [messages, run]);

  const newChat = useCallback(async () => {
    if (busy.current) return;
    const id = threadId.current;
    threadId.current = null;
    setMessages([]);
    if (id) {
      try {
        await api.endSession(id);
      } catch {
        /* the local chat is already cleared; the server forgets idle sessions on restart */
      }
    }
  }, [api]);

  return { messages, pending, send, retry, newChat };
}
