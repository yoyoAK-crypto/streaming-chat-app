import json, os
from dotenv import load_dotenv
from openai import OpenAI
from rag import search_chunks

load_dotenv()
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1", max_retries=6)
USER_ID, K, LIMIT = 20, 5, None                      # LIMIT = None runs every question
APP_MODEL, JUDGE_MODEL = "openai/gpt-oss-20b", "openai/gpt-oss-120b"

JUDGE_PROMPT = """You grade an answer from a document Q&A app. Reply in JSON:
{"supported_claims": int, "total_claims": int, "unsupported": ["..."], "correctness": 1, "reason": "..."}
- Split the answer into factual claims and count how many the SOURCES support.
- correctness: 1 if the answer has the key facts of the REFERENCE, 0.5 if partly right, 0 if wrong.
  If the reference says the document doesn't cover it, give 1 only if the answer says it couldn't find it."""


def ask(model, system, user, as_json=False):
    extra = {"response_format": {"type": "json_object"}} if as_json else {}

    resp = client.chat.completions.create(model=model, temperature=0, **extra,
                                          messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    
    return resp.choices[0].message.content


cases = json.load(open("evals/testset.json", encoding="utf-8"))[:LIMIT]
faith, correct = [], []

for c in cases:
    chunks = [r["content"] for r in search_chunks(USER_ID, c["question"], k=K)]
    sources = "\n\n".join(f"[Source {i + 1}]\n{t}" for i, t in enumerate(chunks))
    answer = ask(APP_MODEL, "Answer using only these sources. If they don't contain the answer, say you couldn't find it.\n\n" + sources, c["question"])

    g = json.loads(ask(JUDGE_MODEL, JUDGE_PROMPT, f"QUESTION: {c['question']}\n\nREFERENCE: {c['reference']}\n\nSOURCES:\n{sources}\n\nANSWER: {answer}", as_json=True))
    correct.append(g["correctness"])

    print(f"\n{c['question']}\n   answer: {answer[:150]}\n   correctness: {g['correctness']}  ({g['reason']})")
    # No factual claims (e.g. "I couldn't find it") means nothing was made up, so score 1.0
    faith.append(g["supported_claims"] / g["total_claims"] if g["total_claims"] else 1.0)
    print(f"   faithfulness: {faith[-1]:.2f}", *[f"\n      unsupported: {u}" for u in g["unsupported"]])

print(f"\nfaithfulness: {sum(faith) / len(faith):.2f}" if faith else "\nfaithfulness: n/a")
print(f"correctness:  {sum(correct) / len(correct):.2f}")

# Correctness gives one overall grade for the whole answer.
# Faithfulness checks claim by claim, which is why it can tell you exactly which sentence was invented (the unsupported list).