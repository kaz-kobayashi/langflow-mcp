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
from mcp_tools import MCP_TOOLS_DEFINITION, execute_mcp_function

load_dotenv()

app = FastAPI(title="AI Chat Agent")

# Initialize database
init_db()

# Templates
templates = Jinja2Templates(directory="templates")

# Static files for visualizations
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    """チャットエンドポイント - ストリーミング対応・Function Calling対応（認証必須）"""

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

            # システムプロンプトを追加してツール使用を強制
            system_message = {
                "role": "system",
                "content": """あなたは在庫最適化の専門アシスタントです。以下のルールに従ってください：

1. 利用可能なツール（function calling）がある場合は、必ずそれを使用してください
2. 各ツールの使い分け：
   - 経済発注量（EOQ）計算 → calculate_eoq（単一品目の発注量最適化）
   - 安全在庫計算 → calculate_safety_stock（単一品目の安全在庫計算、可視化不可）
   - サプライチェーンネットワークの安全在庫最適化 → optimize_safety_stock_allocation（複数品目のネットワーク最適化、可視化可能）
   - グラフや図の可視化 → visualize_last_optimization（optimize_safety_stock_allocationの結果のみ可視化可能）
3. 重要：ユーザーが「可視化したい」「グラフを見たい」と要求した場合：
   - まず optimize_safety_stock_allocation で最適化を実行
   - その後 visualize_last_optimization で可視化
   - calculate_safety_stock の結果は可視化できません
4. Pythonコードやmatplotlibのコードを絶対に生成しないでください
5. ツールで実行できる処理を独自に実装しないでください
6. 複数品目のデータがある場合や、BOM（部品表）が関係する場合は必ず optimize_safety_stock_allocation を使用してください
7. **超重要**: visualize_last_optimizationツールが返すvisualization_urlは、ユーザーが結果を見るための重要なリンクです。
   - このURLを必ずユーザーに伝えてください
   - 「可視化が完了しました」だけでなく、「こちらのリンクをクリックして確認してください: [リンクURL]」のように具体的に提示してください
   - URLを省略したり要約したりしないでください"""
            }

            # メッセージリストを構築（システムメッセージを先頭に追加）
            messages_with_system = [system_message] + [{"role": m.role, "content": m.content} for m in chat_request.messages]

            # OpenAI API呼び出し（Function Calling有効化）
            response = client.chat.completions.create(
                model=chat_request.model,
                messages=messages_with_system,
                tools=MCP_TOOLS_DEFINITION,
                tool_choice="auto",
                stream=False,  # Function Callingの場合はストリーミング無効
            )

            message = response.choices[0].message

            # Function callがある場合
            if message.tool_calls:
                # Function call結果を収集
                function_responses = []

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # MCP関数を実行（user_idを渡す）
                    function_result = execute_mcp_function(function_name, function_args, user_id=current_user.id)

                    function_responses.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_result, ensure_ascii=False)
                    })

                    # Function call結果を送信
                    yield f"data: {json.dumps({'function_call': {'name': function_name, 'result': function_result}})}\n\n"

                # Function call結果を含めて再度LLMを呼び出し
                messages_with_function = [system_message]  # システムメッセージを含める
                messages_with_function.extend([
                    {"role": m.role, "content": m.content} for m in chat_request.messages
                ])
                messages_with_function.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in message.tool_calls
                    ]
                })
                messages_with_function.extend(function_responses)

                # 最終応答を取得（ストリーミング）
                final_stream = client.chat.completions.create(
                    model=chat_request.model,
                    messages=messages_with_function,
                    stream=True,
                )

                assistant_content = ""
                for chunk in final_stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        assistant_content += content
                        yield f"data: {json.dumps({'content': content})}\n\n"

            else:
                # 通常の応答（Function callなし）
                assistant_content = message.content or ""
                yield f"data: {json.dumps({'content': assistant_content})}\n\n"

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
