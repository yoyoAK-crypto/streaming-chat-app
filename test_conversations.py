import uuid
import httpx

BASE = "http://127.0.0.1:8000"
conv = str(uuid.uuid4())


def get_token(username, password="pass1234"):
    httpx.post(f"{BASE}/signup", json={"username": username, "password": password})
    r = httpx.post(f"{BASE}/login", json={"username": username, "password": password})
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


alice = get_token("alice_test")
bob = get_token("bob_test")

# alice starts a new conversation (read the whole stream so the reply gets saved)
with httpx.stream(
    "POST",
    f"{BASE}/chat/stream",
    json={"conversation_id": conv, "message": "Tell me one fun fact about octopuses"},
    headers=auth(alice),
    timeout=60,
) as r:
    "".join(r.iter_text())

r = httpx.get(f"{BASE}/conversations")
print("1. list, no token:", r.status_code)

r = httpx.get(f"{BASE}/conversations", headers=auth(alice))
print("2. alice's list:", r.status_code, [(c["title"], c["id"] == conv) for c in r.json()][:3])

r = httpx.get(f"{BASE}/conversations/{conv}/messages", headers=auth(alice))
print("3. alice's messages:", r.status_code, [m["role"] for m in r.json()])

r = httpx.get(f"{BASE}/conversations", headers=auth(bob))
print("4. bob sees alice's chat in his list:", any(c["id"] == conv for c in r.json()))

r = httpx.get(f"{BASE}/conversations/{conv}/messages", headers=auth(bob))
print("5. bob reads alice's messages:", r.status_code)