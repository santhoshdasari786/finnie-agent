import { useEffect, useRef, useState } from "react";
import { api as defaultApi, type Api } from "./api/client";
import type { AgentInfo } from "./api/types";
import { Composer } from "./components/Composer";
import { Header } from "./components/Header";
import { MessageBubble } from "./components/MessageBubble";
import { Suggestions } from "./components/Suggestions";
import { Tabs, panelId, tabId } from "./components/Tabs";
import { useChat } from "./hooks/useChat";
import { GoalsView } from "./views/GoalsView";
import { MarketView } from "./views/MarketView";
import { PortfolioView } from "./views/PortfolioView";

const TABS = [
  { id: "chat", label: "Chat" },
  { id: "portfolio", label: "Portfolio" },
  { id: "market", label: "Market" },
  { id: "goals", label: "Goals" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function App({ api = defaultApi }: { api?: Api }) {
  const { messages, pending, send, retry, newChat } = useChat(api);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [tab, setTab] = useState<TabId>("chat");
  const [visited, setVisited] = useState<ReadonlySet<TabId>>(new Set(["chat"]));
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

  function choose(id: TabId) {
    setTab(id);
    setVisited((seen) => (seen.has(id) ? seen : new Set(seen).add(id)));
  }

  // A tab is built the first time it is opened and then kept (hidden), so its form and chart survive a visit to another tab.
  const panel = (id: TabId, wide: boolean, children: React.ReactNode, extra = "") =>
    visited.has(id) && (
      <div role="tabpanel" id={panelId(id)} aria-labelledby={tabId(id)} hidden={tab !== id}
           className={`min-h-0 flex-1 flex-col ${extra}`}>
        <div className={`mx-auto w-full ${wide ? "max-w-5xl" : "max-w-3xl"} flex-1 px-4 py-4`}>{children}</div>
      </div>
    );

  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Header agents={agents} onNewChat={newChat} busy={pending} />
      <nav aria-label="Sections" className="border-b border-slate-200 bg-white px-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="mx-auto max-w-5xl">
          <Tabs tabs={[...TABS]} active={tab} onChange={choose} />
        </div>
      </nav>

      <div role="tabpanel" id={panelId("chat")} aria-labelledby={tabId("chat")} hidden={tab !== "chat"}
           className={`min-h-0 flex-1 flex-col ${tab === "chat" ? "flex" : ""}`}>
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

      {panel("portfolio", true, <PortfolioView messages={messages} pending={pending} onSend={send} />, tab === "portfolio" ? "block overflow-y-auto" : "")}
      {panel("market", true, <MarketView api={api} />, tab === "market" ? "block overflow-y-auto" : "")}
      {panel("goals", true, <GoalsView messages={messages} pending={pending} onSend={send} />, tab === "goals" ? "block overflow-y-auto" : "")}
    </div>
  );
}
