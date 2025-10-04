from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import List
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

from database import get_db, init_db, User, ChatHistory
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)

load_dotenv()

app = FastAPI(title="AI Chat Agent")

# Initialize database
init_db()

# Templates
templates = Jinja2Templates(directory="templates")

# OpenAI Client - ローカルまたはクラウド
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "gpt-3.5-turbo"

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """ログインページ"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """チャットページ（認証済みユーザーのみ）"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/register", response_model=Token)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """ユーザー登録"""
    # Check if email already exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """ログイン"""
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/chat")
async def chat(
    chat_request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """チャットエンドポイント - ストリーミング対応（認証必須）"""

    async def generate():
        try:
            # Save user message to database
            user_message = ChatHistory(
                user_id=current_user.id,
                role="user",
                content=chat_request.messages[-1].content
            )
            db.add(user_message)
            db.commit()

            stream = client.chat.completions.create(
                model=chat_request.model,
                messages=[{"role": m.role, "content": m.content} for m in chat_request.messages],
                stream=True,
            )

            assistant_content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    assistant_content += content
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # Save assistant message to database
            assistant_message = ChatHistory(
                user_id=current_user.id,
                role="assistant",
                content=assistant_content
            )
            db.add(assistant_message)
            db.commit()

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
