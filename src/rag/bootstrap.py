"""Dependency-free dummy RAG pipeline."""

from __future__ import annotations

import os
from pathlib import Path
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

import yaml
from src.rag.common.models import Rag
from src.rag.ingestion import embedders, stores                 # noqa: F401  (registers)
from src.rag.retrieval import postprocessors, retrievers        # noqa: F401
from src.rag.glossary import yaml_glossary       
from src.common.models import QASettings                          # NEW: for the Rag dataclass
from src.rag.common.factory import build                   # noqa: F401


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "src" / "config" / "rag.yaml"

def _abs(path: str) -> str:
    p = Path(path)
    return str(p if p.is_absolute() else PROJECT_ROOT / p)

def load_config(config_path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))




def build_rag(config_path: Path = CONFIG_PATH) -> Rag:
    cfg = load_config(config_path)

    # fail if api key is missing
    key_env = cfg["embedder"].get("api_key_env")
    if key_env and not os.environ.get(key_env):
        raise RuntimeError(f"{key_env} is not set. call load_dotenv() in your entry point or export it.")

    # embedder first then the store that is bound to it
    embedder = build("embedder", cfg["embedder"])
    store = build("vector_store",
                  {**cfg["vector_store"], "path": _abs(cfg["vector_store"]["path"])},
                  model_id=embedder.model_id, dimensions=embedder.dimensions)

    store.ensure_collection()

    if store.info().count == 0:
        raise RuntimeError(f"Vector collection '{store.name}' is empty. ...")

    # retriever + post-processors (copy before pop)
    rcfg = dict(cfg["retrieval"])
    processors = [build("postprocessor", s) for s in rcfg.pop("post_processors", [])]
    retriever = build("retriever", rcfg, embedder = embedder, store=store, post_processors=processors)

    # glossary + settings
    glossary = build("glossary", {**cfg["glossary"], "path": _abs(cfg["glossary"]["path"])})
    settings = QASettings.from_config(cfg.get("qa"))

    return Rag(retriever, glossary, settings)
