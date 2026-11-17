import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from src.rag.common.registry import register

@register("manifest", "sqlite")
class SqliteManifest:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute("""CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT, model_id TEXT, content_hash TEXT, n_chunks INTEGER, ingested_at TEXT,
            PRIMARY KEY (doc_id, model_id))""")

    def get_hash(self, doc_id, model_id):
        row = self._db.execute(
            "SELECT content_hash FROM documents WHERE doc_id=? AND model_id=?",
            (doc_id, model_id)).fetchone()
        return row[0] if row else None

    def record(self, doc_id, content_hash, model_id, n_chunks):
        self._db.execute(
            "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?)",
            (doc_id, model_id, content_hash, n_chunks, datetime.now(timezone.utc).isoformat()))
        self._db.commit()
