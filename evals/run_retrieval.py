# Retrieval eval: does search_chunks find a chunk containing each question's evidence phrase?
# Run from the project root: python -m evals.run_retrieval

import json
from rag import search_chunks

USER_ID, K = 20, 5  # whose chunks to search, and how many top results to check


# Normalize quotes, case and whitespace so formatting differences don't cause false misses
def clean(t):
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(t.lower().split())


# Load the test set, skipping unanswerable questions (no evidence to look for)
cases = [c for c in json.load(open("evals/testset.json", encoding="utf-8")) if c["evidence"]]
hits, rr = 0, 0  # questions found, and running total of 1/rank for MRR

for c in cases:
    # Same search the app uses; keep just the chunk texts, best match first
    top = [r["content"] for r in search_chunks(USER_ID, c["question"], k=K)]
    # Position (1 = best) of the first chunk containing the evidence, or None if missing
    rank = next((i for i, text in enumerate(top, 1) if clean(c["evidence"]) in clean(text)), None)
    if rank:
        hits, rr = hits + 1, rr + 1 / rank  # rank 1 adds 1.0, rank 2 adds 0.5, ...
    print(f"{'#' + str(rank) if rank else 'MISS':<5} {c['question']}")  # e.g. "#2" or "MISS"

# hit@K = share found in the top K; MRR = also rewards ranking it high (1.0 = always first)
print(f"\nhit@{K}: {hits / len(cases):.2f}   MRR: {rr / len(cases):.2f}")
