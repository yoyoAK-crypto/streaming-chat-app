from fastembed import TextEmbedding
from fastapi import HTTPException
from pypdf import PdfReader

import numpy as np
from db import SessionLocal
import models 
 

_model = None


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model


def chunk_text(text, size=800, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = text.rfind(" ", start, end)
            if cut > start + size // 2:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


# Turn each text into an "embedding": a list of 384 numbers that captures its meaning.
# Texts with similar meaning get similar numbers, e.g. "cat on a mat" and "kitten on a rug"
# end up close together even though they share almost no words.

def embed_texts(texts):
    # get_model() loads the embedding model once and reuses it.
    # .embed() gives back numpy arrays; .tolist() turns each into a plain Python list
    # so it can be saved in the Postgres ARRAY(Float) column.
    return [v.tolist() for v in get_model().embed(texts)]

def extract_text(file):
    name = (file.filename or "").lower()
    if name.endswith(".pdf"):
        reader = PdfReader(file.file)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    elif name.endswith((".txt", ".md")):
        text = file.file.read().decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Only .pdf, .txt and .md files are supported")
    return " ".join(text.split())

# Find the k chunks of this user's documents whose meaning is closest to the query.
def search_chunks(user_id, query, k=4):
    # Embed the question with the same model used for the chunks, so they can be compared.
    # embed_texts takes a list and returns a list, hence [query] in and [0] out.
    qv = np.array(embed_texts(["Represent this sentence for searching relevant passages: " + query])[0])
    with SessionLocal() as db:
        # Load every chunk that belongs to this user, plus the name of the file it came from.
        # The join links each chunk to its document so we can read Document.filename.
        # Each row is a pair: (Chunk, filename).
        rows = (
            db.query(models.Chunk, models.Document.filename)
            .join(models.Document, models.Chunk.document_id == models.Document.id)
            .filter(models.Chunk.user_id == user_id)  # only this user's documents
            .all()
        )
        if not rows:
            return []  # the user hasn't uploaded anything yet
        # Stack all chunk embeddings into one table (a matrix): one embedded row per chunk, 384 columns.

        mat = np.array([chunk.embedding for chunk, _ in rows])
        # Cosine similarity of every chunk against the query, all at once:
        #   mat @ qv              -> dot product of each chunk with the query (one number per chunk)
        #   np.linalg.norm(...)   -> the length of each vector
        #   dividing by lengths   -> keeps only the direction, i.e. the meaning
        # Scores run from -1 to 1; higher means more similar.
        
        scores = mat @ qv / (np.linalg.norm(mat, axis=1) * np.linalg.norm(qv))
        # argsort gives the positions from lowest to highest score,
        # [::-1] flips it to highest first, and [:k] keeps the top k.
        top = np.argsort(scores)[::-1][:k]
        # Build the results in best-first order. rows[i][0] is the Chunk, rows[i][1] the filename.
        return [
            {
                "filename": rows[i][1],
                "content": rows[i][0].content,
                "score": round(float(scores[i]), 3),
            }
            for i in top
        ]