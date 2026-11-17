function safeUrl(url: string): string | null {
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : null;
  } catch {
    return null;
  }
}

export function LoginPrompt({ url, onSend }: { url: string; onSend: (text: string) => void }) {
  const href = safeUrl(url);
  if (!href) {
    return <p className="mt-3 text-sm text-red-600">The login link couldn't be shown safely. Ask me to connect again.</p>;
  }
  return (
    <div className="mt-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm dark:border-emerald-700 dark:bg-emerald-950/40">
      <p className="mb-2">Log in to Zerodha Kite (read-only access), approve it, then come back here.</p>
      <div className="flex flex-wrap gap-2">
        <a href={href} target="_blank" rel="noopener noreferrer"
           className="rounded-md bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700">
          Open Zerodha login
        </a>
        <button type="button" onClick={() => onSend("connect kite")}
                className="rounded-md border border-emerald-600 px-3 py-1.5 font-medium text-emerald-700 hover:bg-emerald-100 dark:text-emerald-300 dark:hover:bg-emerald-900/40">
          I've approved it
        </button>
      </div>
    </div>
  );
}
