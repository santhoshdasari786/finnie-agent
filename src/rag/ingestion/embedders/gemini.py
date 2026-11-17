import os
import asyncio
from google import genai
from google.genai import types
from src.rag.common.registry import register

@register("embedder", "gemini")
class GeminiEmbedder:
    max_batch_size = 100          # verify against the current API limit

    def __init__(self, model, output_dimensionality, api_key_env,
                 document_prefix="title: {title} | text: {text}",
                 query_prefix="task: search result | query: {text}"):
        self.model_id, self.dimensions = model, output_dimensionality
        self._doc_fmt, self._query_fmt = document_prefix, query_prefix
        self._client = genai.Client(api_key=os.environ[api_key_env])

    def _embed(self, texts):
        resp = self._client.models.embed_content(
            model=self.model_id, 
            contents=[types.Content(parts=[types.Part(text=t)]) for t in texts],
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions))
        return [list(e.values) for e in resp.embeddings]

    def embed_documents(self, texts, titles=None):
        titles = titles or [None] * len(texts)
        return self._embed([self._doc_fmt.format(title=t or "none", text=x)
                            for t, x in zip(titles, texts)])

    # async def embed_query(self, text):
    #     return await asyncio.to_thread(self._embed([self._query_fmt.format(text=text)])[0])

    def embed_query(self, text):
       return self._embed([self._query_fmt.format(text=text)])[0]
