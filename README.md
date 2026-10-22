# Streaming Chat App

A chat app where replies stream in token by token. The assistant can call tools, save notes for each user, and answer questions about documents you upload, citing its sources. Built with FastAPI, PostgreSQL and the Groq API, and runs with one `docker compose up`.

**Live demo:** https://streaming-chat-app.onrender.com
*(Free hosting: the first load after a quiet period takes about a minute while the server wakes up.)*

### Run with Docker

1. Create a `.env` file with `GROQ_API_KEY` and `SECRET_KEY`
2. `docker compose up --build`
3. Open http://localhost:8000

See [Quick start (Docker)](#quick-start-docker) for the full steps.

## Features

**Chat**
- Replies stream over Server-Sent Events (SSE)
- Conversation memory: recent history (the last `MAX_HISTORY` = 20 messages) is loaded from Postgres and sent with every request
- Plain HTML and JavaScript frontend, no framework

**Tool calling**
- The model can call Python functions mid-reply, up to 5 rounds per message
- The page shows which tool is running

| Tool | What it does |
|---|---|
| `get_weather` | Current weather for a city (Open-Meteo) |
| `calculate` | Exact add, subtract, multiply or divide on two numbers |
| `convert_currency` | Converts money using live exchange rates (open.er-api.com) |
| `save_note` | Saves a note for the logged-in user |
| `list_notes` | Lists the user's notes, newest first |
| `search_documents` | Finds the passages in the user's documents that best match a question |

**Documents (RAG)**
- Upload PDF, TXT or Markdown files and ask questions about them
- Answers are based only on the retrieved passages and cite them like `[Source 1]`
- If the documents don't contain the answer, the assistant says so instead of guessing

**Accounts**
- Signup and login with bcrypt-hashed passwords and JWT access tokens
- Conversations, notes and documents belong to one user; other users can't see them

## Quick start (Docker)

You need Docker and a [Groq API key](https://console.groq.com/keys).

1. Clone the repo and create your `.env` from the example:

   ```
   git clone https://github.com/yoyoAK-crypto/streaming-chat-app.git
   cd streaming-chat-app
   cp .env.example .env
   ```

2. In `.env`, fill in `GROQ_API_KEY` and `SECRET_KEY`. Generate a secret key with:

   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   You can leave `DATABASE_URL` as it is: Compose replaces it with the address of its own Postgres container.

3. Build and start everything:

   ```
   docker compose up --build
   ```

4. Open http://localhost:8000, sign up and start chatting.

Compose starts two containers:
- `db`: Postgres 16. Its data is kept in the `pgdata` volume, so it survives restarts.
- `app`: the FastAPI server. It waits until Postgres passes its health check, then runs `init_db.py` and starts uvicorn.

The embedding model is downloaded while the image is built, so document search works straight away.

| Command | What it does |
|---|---|
| `docker compose up --build` | Build and start both containers |
| `docker compose down` | Stop and remove the containers (data is kept) |
| `docker compose down -v` | Also delete the database volume, which **erases all data** |
| `docker compose logs app` | Show the app's output |

## Running without Docker

1. Create a virtual environment and install the packages:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a Postgres database named `chatapp`.

3. Copy `.env.example` to `.env` and fill in all three values. `DATABASE_URL` should point at your local database:

   ```
   GROQ_API_KEY=your_groq_key
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/chatapp
   SECRET_KEY=a_long_random_string
   ```

4. Create the tables:

   ```
   python init_db.py
   ```

5. Start the server and open http://127.0.0.1:8000:

   ```
   uvicorn main:app --reload
   ```

### Database setup

`init_db.py` handles both new and existing databases:
- **New database:** creates every table from the models in `models.py`, then marks the database as up to date with the latest Alembic migration.
- **Existing database:** runs any Alembic migrations it hasn't had yet.

Use it instead of `alembic upgrade head` on a fresh database. The first migration is an empty baseline, so the migrations alone can't build the tables from scratch.

## Deployment

The live demo runs on free tiers:
- **App:** [Render](https://render.com), built from the `Dockerfile`. `init_db.py` runs on every start, so the tables are created or migrated automatically.
- **Database:** [Neon](https://neon.tech) serverless Postgres. Set `DATABASE_URL` in Render's environment settings to your Neon connection string, along with `GROQ_API_KEY` and `SECRET_KEY`.

**Large uploads:** the free Render instance has limited memory, and every chunk of an uploaded file is embedded in one request. Very large documents can run out of memory and fail, so keep uploads small on the demo, or use a paid instance.

## How it works

### How a message flows

1. The page sends JSON plus an `Authorization: Bearer <token>` header to `POST /chat/stream`.
2. The server verifies the token, finds the user and checks that they own the conversation.
3. The user's message is saved, then recent history is loaded from Postgres.
4. The system prompt, history and tool list are sent to Groq (`openai/gpt-oss-20b`), and the reply streams back in chunks.
5. If the model asks for a tool, the server sends `data: {"tool": "<name>"}`, runs the tool, adds the result to the messages and asks the model again.
6. Each text chunk is forwarded to the page as an SSE event: `data: {"text": "..."}`.
7. When the stream ends, the full reply is saved and `data: [DONE]` is sent.

### How document search works

1. `POST /documents` extracts the text from the file and splits it into chunks of about 800 characters, with a 150-character overlap.
2. Each chunk is embedded with `BAAI/bge-small-en-v1.5` (fastembed, 384 dimensions) and stored in Postgres with its owner's user id. Uploading a file with the same name again replaces the old copy.
3. When the model calls `search_documents`, the question is embedded the same way and compared with the user's chunks by cosine similarity. The top 4 are returned as numbered sources.
4. The system prompt tells the model to answer only from those sources, cite them, and say when the answer isn't there.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serves the chat page |
| POST | `/signup` | Create an account |
| POST | `/login` | Returns an access token |
| POST | `/chat/stream` | Streams a reply (auth required) |
| POST | `/documents` | Uploads a .pdf, .txt or .md file for document search (auth required) |
| GET | `/conversations` | Lists your conversations (auth required) |
| GET | `/conversations/{id}/messages` | Returns one conversation's messages (auth required) |

## Evaluation

The RAG pipeline is tested against a book uploaded to the app: *How to Win Friends and Influence People*. The test set, `evals/testset.json`, has 20 questions. Each one has a reference answer and an evidence phrase from the book. 3 of the questions can't be answered from the book, to check that the assistant refuses instead of making something up.

| Metric | Score |
|---|---|
| Retrieval hit@5 | 0.82 |
| Retrieval MRR | 0.62 |
| Answer faithfulness (LLM judge) | 0.99 |
| Answer correctness (LLM judge) | 0.97 |
| Unanswerable questions correctly refused | 3/3 |

- **hit@5:** share of questions where a chunk containing the evidence phrase is in the top 5 results.
- **MRR:** also rewards ranking that chunk high (1.0 = always first).
- **Faithfulness:** share of the answer's factual claims that the retrieved sources support.
- **Correctness:** whether the answer has the key facts of the reference answer (1, 0.5 or 0).

Answers come from `openai/gpt-oss-20b` (the app's model) and are graded by `openai/gpt-oss-120b`. A manual review of all 20 judged answers found 2 judge errors (one too lenient, one too harsh), so the LLM scores are treated as estimates.

### Running the evals

Upload the book through the app first, then set `USER_ID` at the top of each script to the id of the user who uploaded it. Run from the project root:

```
python -m evals.run_retrieval   # hit@5 and MRR
python -m evals.run_judge       # faithfulness and correctness (calls the Groq API)
```

## Project structure

```
main.py             FastAPI app: routes, streaming and the tool-calling loop
tools.py            Tool functions and the tool definitions sent to the model
rag.py              Text extraction, chunking, embeddings and search
auth.py             Password hashing and JWT tokens
models.py           SQLAlchemy tables: users, conversations, messages, notes, documents, chunks
db.py               Database connection
init_db.py          Creates or migrates the database at start-up
index.html          The chat page
alembic/            Database migrations
evals/              RAG test set and evaluation scripts
scripts/            Small debugging helpers for inspecting chunks and embeddings
Dockerfile          Image for the app
docker-compose.yml  Runs the app and Postgres together
```

## Stack

FastAPI, SQLAlchemy, PostgreSQL, Alembic, Groq (through the OpenAI Python SDK), passlib and python-jose. Document search uses fastembed, NumPy and pypdf. Docker and Docker Compose for running it.

## Notes

- Tokens expire after 30 minutes and are kept in memory, so refreshing the page logs you out.
- Each login starts a new conversation.
- Search compares the question with every one of the user's chunks in Python, which is fine for a few documents but would need a vector index (such as pgvector) for large collections.
