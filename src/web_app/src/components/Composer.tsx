import { useState, type KeyboardEvent } from "react";

const MAX = 2000;

export function Composer({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [value, setValue] = useState("");
  const empty = !value.trim();

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="border-t border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          aria-label="Message" rows={2} maxLength={MAX} value={value} disabled={disabled}
          onChange={(e) => setValue(e.target.value)} onKeyDown={onKeyDown}
          placeholder="Ask about investing, tax, your portfolio, a goal or the news…"
          className="min-h-12 flex-1 resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-2 focus:outline-indigo-500 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800"
        />
        <div className="flex flex-col items-end gap-1">
          <button type="submit" disabled={disabled || empty}
                  className="rounded-xl bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
            Send
          </button>
          <span className="text-xs text-slate-500">{value.length} / {MAX}</span>
        </div>
      </div>
    </form>
  );
}
