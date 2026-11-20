import type { Message } from "../api/types";
import { AgentBadge } from "./AgentBadge";
import { Citations } from "./Citations";
import { DataPanel } from "./DataPanel";
import { LoginPrompt } from "./LoginPrompt";
import { QuickReplies } from "./QuickReplies";
import { RichText } from "./RichText";

interface Props {
  message: Message;
  onSend: (text: string) => void;
  onRetry: () => void;
}

export function MessageBubble({ message, onSend, onRetry }: Props) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div aria-label="You" className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div role="alert" className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
        <p>{message.text}</p>
        {message.retryText && (
          <button type="button" onClick={onRetry}
                  className="mt-2 rounded-md border border-red-400 px-3 py-1 font-medium hover:bg-red-100 dark:hover:bg-red-900/40">
            Try again
          </button>
        )}
      </div>
    );
  }

  const r = message.response;
  const team = r.meta?.collaboration?.agents;
  const worked = Array.isArray(team) && team.length > 1 && team.every((a) => typeof a === "string") ? team : null;
  return (
    <div data-testid="assistant-message" data-status={r.status} className="max-w-[92%]">
      <div className="mb-1 flex flex-wrap items-center gap-1">
        {worked ? (
          <p data-testid="collaboration" className="flex flex-wrap items-center gap-1 text-xs text-slate-600 dark:text-slate-300">
            <span>Worked together:</span>
            {worked.map((a, i) => (
              <span key={`${a}-${i}`} className="flex items-center gap-1">
                {i > 0 && <span aria-hidden="true">then</span>}
                <AgentBadge agent={a} />
              </span>
            ))}
          </p>
        ) : (
          <AgentBadge agent={r.agent} />
        )}
      </div>
      <div className="break-words rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <RichText text={r.text} />
        <DataPanel data={r.data} />
        <Citations citations={r.citations} />
        {r.status === "needs_login" && r.login_url && <LoginPrompt url={r.login_url} onSend={onSend} />}
        {r.status === "clarify" && <QuickReplies data={r.data} onSend={onSend} />}
      </div>
      <p className="mt-1 px-1 text-xs text-slate-500 dark:text-slate-400">{r.disclaimer}</p>
    </div>
  );
}
