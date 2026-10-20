from db import SessionLocal
import models


def clean(text):
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(text.lower().split())


phrases = [
    "the greatest asset I possess",
    "the sweetest and most important sound in any language",
    "changing the word “but” to “and”",
]

with SessionLocal() as db:
    chunks = [clean(c.content) for c in db.query(models.Chunk).filter(models.Chunk.user_id == 20)]

for p in phrases:
    print(any(clean(p) in c for c in chunks), "|", p)