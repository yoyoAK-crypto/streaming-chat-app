import json
import uuid
import httpx

BASE = "http://127.0.0.1:8000"


def get_token(username, password="pass1234"):
    httpx.post(f"{BASE}/signup", json={"username": username, "password": password})
    r = httpx.post(f"{BASE}/login", json={"username": username, "password": password})
    return r.json()["access_token"]


def ask(token, conv, text):
    out = ""
    with httpx.stream(
        "POST",
        f"{BASE}/chat/stream",
        json={"conversation_id": conv, "message": text},
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    ) as r:
        for line in r.iter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                out += json.loads(line[6:])["text"]
    return out


token = get_token("alice_test")
conv = str(uuid.uuid4())

for msg in ["My name is Sam. Remember it.", "Name a color.", "Name an animal.", "Name a fruit."]:
    ask(token, conv, msg)

print(ask(token, conv, "What is my name?"))