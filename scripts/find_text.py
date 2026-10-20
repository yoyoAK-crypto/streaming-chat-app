import sys
from db import SessionLocal
import models

word = sys.argv[1].lower()

with SessionLocal() as db:
    for c in db.query(models.Chunk).filter(models.Chunk.user_id == 20):
        i = c.content.lower().find(word)
        if i != -1:
            print(f"--- chunk {c.id} ---")
            print(c.content[max(0, i - 100): i + 150])
            print()