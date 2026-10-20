import random
import sys

from db import SessionLocal
import models

USER_ID = 20   # the user who owns the book
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 3

with SessionLocal() as db:
    chunks = db.query(models.Chunk).filter(models.Chunk.user_id == USER_ID).all()
    print(f"{len(chunks)} chunks total\n")
    for c in random.sample(chunks, min(COUNT, len(chunks))):
        print(f"=== chunk {c.id} ===")
        print(c.content)
        print()