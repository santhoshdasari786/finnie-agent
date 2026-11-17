import argparse
import yaml
from dotenv import load_dotenv

from src.rag.ingestion import embedders, stores                 # noqa: F401  (registers)
from src.rag.retrieval import postprocessors, retrievers        # noqa: F401  (registers)
from src.rag.common.factory import build
from src.rag.common.models import RetrievalQuery

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--config", default="src/config/rag.yaml")
    ap.add_argument("--category")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    load_dotenv()
    cfg = yaml.safe_load(open(args.config))

    embedder = build("embedder", cfg["embedder"])
    store = build("vector_store", cfg["vector_store"],
                  model_id=embedder.model_id, dimensions=embedder.dimensions)
    store.ensure_collection()
    if store.info().count == 0:
        raise SystemExit(f"Collection {store.name} is empty. Wrong model, or nothing ingested?")

    rcfg = dict(cfg["retrieval"])
    processors = [build("postprocessor", s) for s in rcfg.pop("post_processors", [])]
    retriever = build("retriever", rcfg, embedder=embedder, store=store,
                      post_processors=processors)

    result = retriever.retrieve(RetrievalQuery(args.question, category=args.category, k=args.k))
    print(result.status, "best:", result.best_score)
    for h in result.chunks:
        print(f"{h.score:.3f}  {h.title}  [{h.chunk_id}]\n      {h.text[:100]!r}")

if __name__ == "__main__":
    main()
