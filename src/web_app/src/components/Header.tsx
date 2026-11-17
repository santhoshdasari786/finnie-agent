import type { AgentInfo } from "../api/types";
import { AGENT_LABELS } from "./AgentBadge";

interface Props {
  agents: AgentInfo[];
  onNewChat: () => void;
  busy: boolean;
}

export function Header({ agents, onNewChat, busy }: Props) {
  return (
    <header className="border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Finnie</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">A finance education assistant</p>
        </div>
        <div className="flex items-center gap-3">
          {agents.length > 0 && (
            <ul aria-label="Agent status" className="hidden items-center gap-1.5 sm:flex">
              {agents.map((a) => {
                const label = AGENT_LABELS[a.name] ?? a.name;
                return (
                  <li key={a.name} aria-label={`${label}: ${a.ready ? "ready" : "not available"}`} title={`${label}: ${a.ready ? "ready" : "not available"}`}
                      className={`size-2.5 rounded-full ${a.ready ? "bg-emerald-500" : "bg-slate-400"}`} />
                );
              })}
            </ul>
          )}
          <button type="button" onClick={onNewChat} disabled={busy}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:hover:bg-slate-800">
            New chat
          </button>
        </div>
      </div>
    </header>
  );
}
