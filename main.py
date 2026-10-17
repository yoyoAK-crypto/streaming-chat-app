import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import json
from datetime import datetime

import models
from db import engine, SessionLocal, Base, get_db
from models import Conversation, Message, User
from auth import hash_password, verify_password, create_access_token, get_current_user

from tools import TOOLS, AVAILABLE_TOOLS

load_dotenv()

client = OpenAI(
    api_key =os.getenv('GROQ_API_KEY'),
    base_url="https://api.groq.com/openai/v1",
)


class ChatRequest(BaseModel):
    conversation_id: str
    message: str

class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    model_config = {"from_attributes": True}

class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    role: str
    content: str
    model_config = {"from_attributes": True}

def get_current_db_user(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

app = FastAPI()
MODEL = "openai/gpt-oss-20b"

SYSTEM_PROMPT = (
    "You are Atlas, a friendly assistant for someone learning AI engineering. "
    "Keep answers short and clear, use plain language, and give a small example "
    "when you explain something."
)

MAX_HISTORY = 20
USER_TOOLS = {"save_note", "list_notes"}

@app.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user.id)
        .order_by(models.Conversation.created_at.desc())
        .all()
    )


@app.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: str,
    user: models.User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
):
    conversation = db.get(models.Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.id)
        .all()
    )



@app.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = models.User(
        username=user.username,
        hashed_password=hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)): # Call 'get_db' for me, and pass the result in.
    existing = db.query(models.User).filter(models.User.username == user.username).first()

    if not existing or not verify_password(user.password, existing.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token({"sub": existing.username}) # This dictionary is the payload
    # 'create_access_token'adds an expiry time to the payload: "exp", set 30 minutes from now jwt.encode(...) signs the payload with your SECRET_KEY and produces the long string. 
    # That's the token, and it's saved in the variable token.
    return {"access_token": token, "token_type": "bearer"}

    # Anyone can read a token's payload, but nobody can change it (for example, swap the username) without breaking the signature, unless they have your secret key.
    # The server can therefore trust any token that verifies.
@app.get("/")
def index():
    return FileResponse("index.html") # The server sends back index.html. The browser shows your chat page.


@app.post("/chat")
def chat(request: ChatRequest):# FastAPI parses the JSON body into this object, and Pydantic rejects a bad body before the function runs
    response = client.chat.completions.create( # "given a chat so far, complete it with the next message." .create(...) is the action: make one request now
        model= MODEL,
        messages=[{"role": "user", "content": request.message}], # a list of dicts. Each has a role ("user" or "assistant") and content. For now it holds one message.
         # You'll later append earlier turns to this list, which is how the model gets memory
    )
    return {"reply": response.choices[0].message.content}



def stream_with_tools(messages, user_id, max_rounds=5):
    """Yields ("text", piece) and ("tool", name) items, running tools as needed."""
    for _ in range(max_rounds):
        stream = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, stream=True
        )

        text = ""
        calls = {}  # tool call index -> collected id, name and arguments

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                text += delta.content
                yield ("text", delta.content)

            for tc in delta.tool_calls or []:
                entry = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    entry["id"] = tc.id
                if tc.function and tc.function.name:
                    entry["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    entry["arguments"] += tc.function.arguments

        # no tool requested: the streamed text was the final answer
        if not calls:
            return

        ordered = [calls[i] for i in sorted(calls)]
        messages.append(
            {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"]},
                    }
                    for c in ordered
                ],
            }
        )

        for c in ordered:
            yield ("tool", c["name"])
            try:
                args = json.loads(c["arguments"] or "{}")
                if c["name"] in USER_TOOLS:
                    args["user_id"] = user_id  # overwrite anything the model sent
                    result = AVAILABLE_TOOLS[c["name"]](**args)
            except Exception as e:
                result = {"error": f"Tool failed: {e}"}
            print(f"[tool] {c['name']}({c['arguments']}) -> {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": c["id"],
                    "content": json.dumps(result),
                }
            )


@app.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    conversation_id = request.conversation_id
    conversation = db.get(models.Conversation, conversation_id)
    if conversation is None:
        db.add(models.Conversation(id=conversation_id, user_id=user.id, title=request.message[:40]))
        db.commit()
    elif conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.add(models.Message(conversation_id=conversation_id, role="user", content=request.message))
    db.commit()

    rows = (
        db.query(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.id.desc())
        .limit(MAX_HISTORY)
        .all()
    )
    rows.reverse()
    history = [{"role": m.role, "content": m.content} for m in rows]

    def event_stream():
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
        full_reply = ""

        for kind, value in stream_with_tools(messages, user.id):
            if kind == "tool":
                yield f"data: {json.dumps({'tool': value})}\n\n"
            else:
                full_reply += value
                yield f"data: {json.dumps({'text': value})}\n\n"

        with SessionLocal() as save_db:
            save_db.add(models.Message(conversation_id=conversation_id, role="assistant", content=full_reply))
            save_db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")