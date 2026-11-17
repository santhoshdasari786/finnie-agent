export const SUGGESTIONS = [
  "What is a SIP and how does it work?",
  "How are capital gains taxed in India?",
  "Can I reach 50 lakh in 10 years saving 20k a month?",
  "Latest news on Infosys",
  "What is the Nifty trading at today?",
  "connect to my portfolio",
];

export function Suggestions({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="mt-4 flex flex-wrap justify-center gap-2">
      {SUGGESTIONS.map((s) => (
        <button key={s} type="button" onClick={() => onPick(s)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700">
          {s}
        </button>
      ))}
    </div>
  );
}
