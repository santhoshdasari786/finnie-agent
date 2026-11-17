import logging
import os

from dotenv import load_dotenv

load_dotenv(".env")

from src.api.app import create_app  # noqa: E402

logging.basicConfig(level=logging.WARNING)
logging.getLogger("src.workflow").setLevel(logging.INFO)

_origins = [o.strip() for o in os.getenv("FINNIE_CORS_ORIGINS", "").split(",") if o.strip()]
app = create_app(cors_origins=_origins or None)
