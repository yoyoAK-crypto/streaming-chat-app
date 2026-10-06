# Streaming Chat App

A chat app where replies stream in token by token. Built with FastAPI, Postgres and the Groq API, with per-user accounts and conversation history.

## Features

- Streaming replies over Server-Sent Events (SSE)
- Conversation memory: the full history is loaded from Postgres and sent to the model on every request
- Signup and login with bcrypt-hashed passwords and JWT access tokens
- Each conversation belongs to a user; other users get a 404 for it
- Schema changes managed with Alembic migrations
- Plain HTML and JavaScript frontend (no framework)

## Stack

FastAPI, SQLAlchemy, PostgreSQL, Alembic, Groq (through the OpenAI Python SDK), passlib and python-jose.

## How a message flows

1. The page sends JSON plus an `Authorization: Bearer <token>` header to `POST /chat/stream`.
2. The server verifies the token, finds the user and checks conversation ownership.
3. The user's message is saved, then the full history is loaded from Postgres.
4. The history is sent to Groq, and the reply streams back in chunks.
5. Each chunk is forwarded to the page as an SSE event: `data: {"text": "..."}`.
6. When the stream ends, the full reply is saved and `data: [DONE]` is sent.

## Setup

1. Clone the repo and create a virtual environment:

```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
```

2. Create a Postgres database named `chat_app`.

3. Create a `.env` file in the project root:

```
   GROQ_API_KEY=your_groq_key
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/chat_app
   SECRET_KEY=a_long_random_string
```

   Generate a secret key with:

```
   python -c "import secrets; print(secrets.token_hex(32))"
```

4. Create the tables:

```
   alembic upgrade head
```

5. Start the server:

```
   uvicorn main:app --reload
```

6. Open http://127.0.0.1:8000, sign up and start chatting.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/signup` | Create an account |
| POST | `/login` | Returns an access token |
| POST | `/chat/stream` | Streams a reply (auth required) |
| GET | `/` | Serves the chat page |
| GET | `/conversations` | Lists your conversations (auth required) |
| GET | `/conversations/{id}/messages` | Returns one conversation's messages (auth required) |

## Notes

- Tokens expire after 30 minutes and are kept in memory, so refreshing the page logs you out.
- Each login starts a new conversation.