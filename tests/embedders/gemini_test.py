"""Live check of the embedding API's two accepted input shapes (needs GOOGLE_API_KEY; two embedding calls).

Run:  .venv/bin/python -m pytest tests/embedders -v
Skipped without a key, and skipped (not failed) when the free tier's quota is used up, so it can never break the rest of the suite.
"""
import os

import pytest
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

pytestmark = pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="live test: needs GOOGLE_API_KEY")

TEXTS = ["what is a SIP", "what is compound interest", "what is a bond"]


def embed(contents):
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    try:
        return client.models.embed_content(model="gemini-embedding-2", contents=contents,
                                           config=types.EmbedContentConfig(output_dimensionality=768))
    except errors.ClientError as e:
        if getattr(e, "code", None) == 429:
            pytest.skip("embedding quota exhausted (free tier: 100 a minute, 1,000 a day)")
        raise


def test_a_plain_list_of_strings_gives_one_vector_per_text():
    assert len(embed(TEXTS).embeddings) == 3


def test_one_content_object_per_text_gives_one_vector_per_text():
    contents = [types.Content(parts=[types.Part(text=t)]) for t in TEXTS]
    result = embed(contents)
    assert len(result.embeddings) == 3 and all(len(e.values) == 768 for e in result.embeddings)
