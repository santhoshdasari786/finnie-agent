import argparse, logging
import yaml
from dotenv import load_dotenv

from src.rag.ingestion import chunkers, embedders, loaders, manifest, stores  # noqa: F401  (registers)
from src.rag.common.factory import build
from src.rag.ingestion.core.ingestion import IngestionPipeline

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    load_dotenv()
    cfg = yaml.safe_load(open(args.config))
    logging.basicConfig(level=logging.INFO)

    embedder = build("embedder", cfg["embedder"])
    store = build("vector_store", cfg["vector_store"],
                  model_id=embedder.model_id, dimensions=embedder.dimensions)
    pipeline = IngestionPipeline(
        loaders=[build("loader", s) for s in cfg["sources"]],
        cleaners=[build("cleaner", c) for c in cfg.get("cleaners", [])],
        chunker=build("chunker", cfg["chunker"]),
        embedder=embedder, store=store,
        manifest=build("manifest", cfg["manifest"]),
        **cfg.get("pipeline", {}),
    )
    stats = pipeline.run()
    print(stats, store.info())

if __name__ == "__main__":
    main()
