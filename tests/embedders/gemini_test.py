from google import genai
from google.genai import types
import os
from dotenv import load_dotenv; load_dotenv()

c = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
cfg = types.EmbedContentConfig(output_dimensionality=768)
texts = ["what is a SIP", "what is compound interest", "what is a bond"]

# A: plain list of strings (what the code does now)
r = c.models.embed_content(model="gemini-embedding-2", contents=texts, config=cfg)
print("A plain list:", len(r.embeddings))

# B: one Content object per text
r = c.models.embed_content(
    model="gemini-embedding-2",
    contents=[types.Content(parts=[types.Part(text=t)]) for t in texts],
    config=cfg)
print("B Content each:", len(r.embeddings))
