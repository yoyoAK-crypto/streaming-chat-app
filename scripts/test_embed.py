from fastembed import TextEmbedding
import numpy as np

model = TextEmbedding("BAAI/bge-small-en-v1.5")

texts = [
    "The cat sat on the mat",
    "A kitten is resting on a rug",
    "Stock markets fell sharply today",
]
vectors = [np.array(v) for v in model.embed(texts)]

print("vector length:", len(vectors[0]))

def cosine(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

print("cat vs kitten:", cosine(vectors[0], vectors[1]))
print("cat vs stocks:", cosine(vectors[0], vectors[2]))