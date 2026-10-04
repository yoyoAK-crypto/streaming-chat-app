import httpx


def send(message):
    with httpx.stream(
        "POST",
        "http://127.0.0.1:8000/chat/stream",
        json={"conversation_id": "test2", "message": message},
        timeout=60,
    ) as r:
        for line in r.iter_lines():
            if line:
                print(line, flush=True)



send("Write two short paragraphs about dogs, then a bulleted list of 3 items.")