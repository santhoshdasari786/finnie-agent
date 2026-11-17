"""Measure retrieval score distributions per question group and suggest retrieval.min_score.

Run from the project root:   .venv/bin/python -m scripts.eval_retrieval
Needs GOOGLE_API_KEY (one embedding call per question, ~50 calls) and a built vector store.

It bypasses the post-processors on purpose: we want the RAW best score, before the threshold hides it.
The glossary is also bypassed: this measures retrieval only.
"""
import statistics
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from src.rag.bootstrap import build_rag                     # noqa: E402  (after load_dotenv)
from src.rag.common.models import RetrievalQuery            # noqa: E402

QUESTIONS = ROOT / "tests" / "eval" / "questions.yaml"
K = 5


def run_group(retriever, items):
    rows = []
    for it in items:
        res = retriever.retrieve(RetrievalQuery(it["q"], k=K))
        docs = [c.metadata.get("doc_id") for c in res.chunks]
        rows.append({
            "q": it["q"], "expect": it.get("expect"),
            "best": res.best_score or 0.0,
            "top": docs[0] if docs else None,
            "hit1": bool(docs) and docs[0] == it.get("expect"),
            "hit3": it.get("expect") in docs[:3],
        })
    return rows


def show(name, rows):
    print(f"\n=== {name} ({len(rows)})")
    for r in sorted(rows, key=lambda r: r["best"]):
        flag = ""
        if r["expect"]:
            flag = "ok " if r["hit1"] else ("hit3" if r["hit3"] else "MISS")
        print(f"  {r['best']:.3f} {flag:4} {r['q'][:62]:62} -> {r['top']}")
    scores = [r["best"] for r in rows]
    print(f"  min {min(scores):.3f}  median {statistics.median(scores):.3f}  max {max(scores):.3f}")


def main():
    data = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    rag = build_rag()
    rag.retriever.post_processors = []                       # raw scores

    groups = {name: run_group(rag.retriever, data[name]) for name in ("in_kb", "borderline", "off_topic")}
    for name, rows in groups.items():
        show(name, rows)

    kb = [r["best"] for r in groups["in_kb"]]
    off = [r["best"] for r in groups["off_topic"]]
    border = [r["best"] for r in groups["borderline"]]

    print("\n=== retrieval quality (in_kb)")
    n = len(groups["in_kb"])
    print(f"  top-1 correct: {sum(r['hit1'] for r in groups['in_kb'])}/{n}   "
          f"top-3 contains expected: {sum(r['hit3'] for r in groups['in_kb'])}/{n}")

    print("\n=== threshold sweep   (wrongly refused in_kb | wrongly answered off_topic | borderline answered)")
    for t in [x / 100 for x in range(50, 80, 2)]:
        refused = sum(s < t for s in kb)
        leaked = sum(s >= t for s in off)
        answered = sum(s >= t for s in border)
        print(f"  min_score {t:.2f}:  {refused:2} | {leaked:2} | {answered:2}/{len(border)}")

    gap = min(kb) - max(off)
    print(f"\nlowest in_kb {min(kb):.3f}  vs  highest off_topic {max(off):.3f}  -> gap {gap:+.3f}")
    if gap > 0:
        print(f"separable: any min_score in ({max(off):.3f}, {min(kb):.3f}]; midpoint {(max(off) + min(kb)) / 2:.3f}")
    else:
        print("NOT separable by score alone: the groups overlap. Consider a router/market-agent handoff or reranking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
