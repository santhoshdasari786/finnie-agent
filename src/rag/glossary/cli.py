import argparse
import yaml

from src.rag.glossary import yaml_glossary                      # noqa: F401  (registers)
from src.rag.common.factory import build


def main():
    ap = argparse.ArgumentParser(description="Look up a term in the glossary")
    ap.add_argument("question", help='e.g. "what is an ETF?"')
    ap.add_argument("--config", default="src/config/rag.yaml")
    ap.add_argument("--fuzzy", type=float, help="override fuzzy_cutoff, e.g. 0.85")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))["glossary"]
    if args.fuzzy is not None:
        cfg["fuzzy_cutoff"] = args.fuzzy
    glossary = build("glossary", cfg)

    match = glossary.lookup(args.question)
    if match is None:
        print("NO MATCH  → would fall through to RAG")
        return

    print(f"{match.match_type.upper()} match on {match.matched_text!r}"
          f"{'  (AMBIGUOUS: ask a clarifying question)' if match.ambiguous else ''}")
    for e in match.entries:
        label = f"{e.term} ({e.sense})" if e.sense else e.term
        print(f"\n• {label}\n  {e.definition}")
        if e.related_articles:
            print(f"  read more: {', '.join(e.related_articles)}")
        if e.source_urls:
            print(f"  sources:   {', '.join(e.source_urls)}")


if __name__ == "__main__":
    main()
