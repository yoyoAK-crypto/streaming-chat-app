import httpx

BASE = "http://127.0.0.1:8000"
conv = "protected-test-2"


def get_token(username, password="pass1234"):
    httpx.post(f"{BASE}/signup", json={"username": username, "password": password})
    r = httpx.post(f"{BASE}/login", json={"username": username, "password": password})
    return r.json()["access_token"]


def chat(token, text):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.stream(
        "POST",
        f"{BASE}/chat/stream",
        json={"conversation_id": conv, "message": text},
        headers=headers,
        timeout=60,
    ) as r:
        body = "".join(r.iter_text())
        return r.status_code, body[:80]


alice = get_token("alice_test")
bob = get_token("bob_test")

print("1. no token:", chat(None, "hi"))
print("2. alice:   ", chat(alice, "Say hello in five words"))
print("3. bob on alice's conversation:", chat(bob, "hi"))