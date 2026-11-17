import type { ReactNode } from "react";

type Block = { type: "p"; text: string } | { type: "ul"; items: string[] };

function parse(text: string): Block[] {
  const blocks: Block[] = [];
  let para: string[] = [];
  let items: string[] = [];
  const flushPara = () => {
    if (para.length) blocks.push({ type: "p", text: para.join("\n") });
    para = [];
  };
  const flushItems = () => {
    if (items.length) blocks.push({ type: "ul", items });
    items = [];
  };
  for (const line of text.split("\n")) {
    const bullet = /^\s*-\s+(.*)$/.exec(line);
    if (!line.trim()) {
      flushPara();
      flushItems();
    } else if (bullet) {
      flushPara();
      items.push(bullet[1]);
    } else {
      flushItems();
      para.push(line);
    }
  }
  flushPara();
  flushItems();
  return blocks;
}

/** **bold** only. Everything else, including anything that looks like HTML, stays plain text. */
function Inline({ text }: { text: string }): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  );
}

export function RichText({ text }: { text: string }) {
  const blocks = parse(text);
  if (!blocks.length) return null;
  return (
    <div className="space-y-2">
      {blocks.map((b, i) =>
        b.type === "p" ? (
          <p key={i} className="whitespace-pre-line">
            <Inline text={b.text} />
          </p>
        ) : (
          <ul key={i} className="list-disc space-y-1 pl-5">
            {b.items.map((item, j) => (
              <li key={j}>
                <Inline text={item} />
              </li>
            ))}
          </ul>
        ),
      )}
    </div>
  );
}
