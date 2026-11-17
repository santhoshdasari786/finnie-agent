import { useEffect, useRef, useState } from "react";
import { api as defaultApi, type Api } from "./api/client";
import type { AgentInfo } from "./api/types";
import { Composer } from "./components/Composer";
import { Header } from "./components/Header";
import { MessageBubble } from "./components/MessageBubble";
import { Suggestions } from "./components/Suggestions";
import { useChat } from "./hooks/useChat";

export default function App({ api = defaultApi }: { api?: Api }) {
  const { messages, pending, send, retry, newChat } = useChat(api);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    api.agents().then((list) => alive && setAgents(list)).catch(() => {});
    return () => {
      alive = false;
    };
  }, [api]);

  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, pending]);

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Header agents={agents} onNewChat={newChat} busy={pending} />
      <main role="log" aria-live="polite" className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && (
            <div className="py-12 text-center">
              <h2 className="text-2xl font-semibold">What would you like to know?</h2>
              <p className="mt-2 text-slate-600 dark:text-slate-400">
                Ask about investing basics, tax, prices, your portfolio, a savings goal or the news.
              </p>
              <Suggestions onPick={send} />
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} onSend={send} onRetry={retry} />
          ))}
          {pending && (
            <p role="status" className="text-sm text-slate-500 dark:text-slate-400">Finnie is thinking…</p>
          )}
          <div ref={end} />
        </div>
      </main>
      <Composer onSend={send} disabled={pending} />
    </div>
  );
}
