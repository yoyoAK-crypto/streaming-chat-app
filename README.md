# Streaming Chat App

A chat app where replies stream in token by token. Built with FastAPI, Postgres and the Groq API, with per-user accounts and conversation history.

## Features

- Streaming replies over Server-Sent Events (SSE)
- Conversation memory: the full history is loaded from Postgres and sent to the model on every request
- Signup and login with bcrypt-hashed passwords and JWT access tokens
- Each conversation belongs to a user; other users get a 404 for it
- Schema changes managed with Alembic migrations
- Plain HTML and JavaScript frontend (no framework)
- Configurable system prompt and capped history window (MAX_HISTORY)
- Tool calling: the model can call Python functions mid-reply (up to 5 rounds per message), and the page shows which tool is running
- Per-user notes stored in Postgres, which the model saves and lists through tools
- RAG over uploaded documents: upload PDF, TXT or Markdown files and ask questions about them, with answers citing their sources

### Tools

| Tool | What it does |
|---|---|
| `get_weather` | Current weather for a city (Open-Meteo) |
| `calculate` | Exact add, subtract, multiply or divide on two numbers |
| `convert_currency` | Converts money using live exchange rates (open.er-api.com) |
| `save_note` | Saves a note for the logged-in user |
| `list_notes` | Lists the user's notes, newest first |
| `search_documents` | Finds the passages in the user's documents that best match a question |

### How document search works

1. `POST /documents` extracts the text from the file and splits it into chunks of about 800 characters, with a 150-character overlap.
2. Each chunk is embedded with `BAAI/bge-small-en-v1.5` (fastembed, 384 dimensions) and stored in Postgres with its owner's user id. Uploading a file with the same name again replaces the old copy.
3. When the model calls `search_documents`, the query is embedded and compared with the user's chunks by cosine similarity, and the top 4 are returned as numbered sources.
4. The model answers using only those sources and cites them like `[Source 1]`.

Users can only search their own documents.

## Stack

FastAPI, SQLAlchemy, PostgreSQL, Alembic, Groq (through the OpenAI Python SDK), passlib and python-jose. Document search uses fastembed, NumPy and pypdf.

## How a message flows

1. The page sends JSON plus an `Authorization: Bearer <token>` header to `POST /chat/stream`.
2. The server verifies the token, finds the user and checks conversation ownership.
3. The user's message is saved, then the full history is loaded from Postgres.
4. The history and the tool list are sent to Groq, and the reply streams back in chunks.
5. If the model asks for a tool, the server sends `data: {"tool": "<name>"}`, runs the tool, adds the result to the messages and asks the model again.
6. Each text chunk is forwarded to the page as an SSE event: `data: {"text": "..."}`.
7. When the stream ends, the full reply is saved and `data: [DONE]` is sent.

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
| POST | `/documents` | Uploads a .pdf, .txt or .md file for document search (auth required) |
| GET | `/` | Serves the chat page |
| GET | `/conversations` | Lists your conversations (auth required) |
| GET | `/conversations/{id}/messages` | Returns one conversation's messages (auth required) |

## Evaluation

RAG results from the scripts in `evals/` (`run_retrieval.py` and `run_judge.py`, using `testset.json`):

| Metric | Score |
|---|---|
| Retrieval hit@5 | 0.82 |
| Retrieval MRR | 0.62 |
| Answer faithfulness (LLM judge) | 0.99 |
| Answer correctness (LLM judge) | 0.97 |
| Unanswerable questions correctly refused | 3/3 |

A manual review of all 20 judged answers found 2 judge errors (one too lenient, one too harsh), so the LLM scores are treated as estimates.

## Notes

- Tokens expire after 30 minutes and are kept in memory, so refreshing the page logs you out.
- Each login starts a new conversation.