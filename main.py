from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
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
    get_current_user,
    get_current_user_optional
)
from mcp_tools import MCP_TOOLS_DEFINITION, execute_mcp_function, get_visualization_html

load_dotenv()

app = FastAPI(title="AI Chat Agent")

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SKIP_AUTH = ENVIRONMENT == "local"  # ローカル環境では認証をスキップ

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
    model: str = os.getenv("OPENAI_MODEL_NAME", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

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
    """ホームページ - ローカル環境ではチャット画面、本番環境ではログイン画面"""
    if SKIP_AUTH:
        # ローカル環境では直接チャット画面を表示
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        # 本番環境ではログイン画面を表示
        return templates.TemplateResponse("login.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """チャットページ"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/config")
async def get_config():
    """フロントエンド用の設定情報を返す"""
    return {
        "model": os.getenv("OPENAI_MODEL_NAME", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        "environment": ENVIRONMENT,
        "skip_auth": SKIP_AUTH
    }

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
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """チャットエンドポイント - ストリーミング対応・Function Calling対応"""

    async def generate():
        try:
            # Save user message to database (if user is logged in)
            if current_user:
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
                "content": """You are an inventory optimization assistant. You have access to multiple tools (functions) to help users.

**IMPORTANT RULES:**
1. ALWAYS use available tools/functions when appropriate - do NOT perform calculations manually
2. When user provides parameters for EOQ, safety stock, or other calculations, immediately call the corresponding function
3. Respond in Japanese (日本語) for all text output

あなたは在庫最適化の専門アシスタントです。以下のルールに従ってください：

**重要: ユーザーからパラメータが提供された場合は、必ず対応するツール（function）を呼び出してください。手動で計算しないでください。**

1. 利用可能なツール（function calling）がある場合は、必ずそれを使用してください
2. 各ツールの使い分け：
   - 経済発注量（EOQ）計算（推奨：_rawバージョンを使用）:
     * 基本EOQ → calculate_eoq_raw（年間需要、発注コスト、保管費率、単価をそのまま渡す）
     * 増分数量割引EOQ → calculate_eoq_incremental_discount_raw（発注量に応じて段階的に単価が下がる）
     * 全単位数量割引EOQ → calculate_eoq_all_units_discount_raw（発注量に応じて全数量の単価が下がる）
   - EOQ可視化 → visualize_eoq（calculate_eoq_*_rawの後に使用。パラメータ不要）
   - 安全在庫計算 → calculate_safety_stock（単一品目の安全在庫計算、可視化不可）
   - サプライチェーンネットワークの安全在庫最適化 → optimize_safety_stock_allocation（複数品目のネットワーク最適化、可視化可能）
   - グラフや図の可視化 → visualize_last_optimization（optimize_safety_stock_allocationの結果のみ可視化可能）
   - **基在庫シミュレーション（分布ベース）** → base_stock_simulation_using_dist（確率分布パラメータから需要を自動生成してシミュレーション実行）
   - 基在庫シミュレーション（需要配列） → simulate_base_stock_policy（需要配列が既にある場合のみ使用）
3. 重要：基在庫シミュレーションのツール選択：
   - ユーザーが「正規分布」「ガンマ分布」など分布タイプと統計パラメータ（平均、標準偏差など）を指定した場合 → **base_stock_simulation_using_dist を使用**
   - ユーザーが具体的な需要配列（例: [98, 105, 92, ...]）を提供した場合 → simulate_base_stock_policy を使用
   - 絶対に需要配列の生成を要求しないこと！分布パラメータがあれば base_stock_simulation_using_dist が自動生成します
4. 重要：EOQ計算の手順（Two-Step Processing）：
   - ユーザーが年間需要、発注コスト、保管費率、単価（テーブル）を指定した場合
   - **必ず_rawバージョンのFunction（calculate_eoq_*_raw）を使用してください**
   - ユーザーから受け取った値をそのまま渡してください（パラメータ変換は自動的に行われます）
   - 例：年間需要15000個、発注コスト500円、保管費率25%、単価テーブル → そのまま渡す
5. 重要：定期発注最適化（optimize_periodic_inventory）のパラメータ指定：
   - 段階ごとに異なる値（例: 在庫保管費用: [0.5, 1.0, 2.0, 5.0]）が指定された場合：
     * 各段階のhフィールドに配列の対応する値を設定してください（Stage0はh=0.5, Stage1はh=1.0など）
   - 全段階共通の値（例: バックオーダーコスト: 100）が指定された場合：
     * トップレベルのbackorder_costパラメータに設定してください（各段階のbフィールドは省略可能）
   - リードタイムが配列で指定された場合（例: [3, 2, 2, 1]）：
     * 各段階のnet_replenishment_timeフィールドに配列の対応する値を設定してください
6. 重要：ユーザーが「可視化したい」「グラフを見たい」と要求した場合：
   - **EOQの可視化**：EOQ計算（calculate_eoq_*_raw）を実行した直後に visualize_eoq を呼び出す
   - **安全在庫ネットワークの可視化**：optimize_safety_stock_allocation で最適化を実行した後に visualize_last_optimization で可視化
   - calculate_safety_stock（単一品目）の結果は可視化できません
7. Pythonコードやmatplotlibのコードを絶対に生成しないでください
8. ツールで実行できる処理を独自に実装しないでください
9. 複数品目のデータがある場合や、BOM（部品表）が関係する場合は必ず optimize_safety_stock_allocation を使用してください
10. **最重要ルール**: 可視化ツール（visualize_eoq, visualize_last_optimization）の応答について：
   - これらのツールが成功すると、自動的に可視化リンクが表示されます
   - あなたは「可視化が完了しました。上に表示されたリンクをクリックして確認してください。」とだけ伝えてください
   - URLを自分で提示する必要はありません（システムが自動的に表示します）"""
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
                    user_id = current_user.id if current_user else None
                    function_result = execute_mcp_function(function_name, function_args, user_id=user_id)

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

            # Save assistant message to database (if user is logged in)
            if current_user:
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

@app.get("/api/visualization/{viz_id}", response_class=HTMLResponse)
async def get_visualization(viz_id: str):
    """可視化HTMLを取得（認証不要 - viz_idはUUIDで推測困難）"""
    try:
        # ファイルシステムから可視化HTMLを読み込む
        output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
        file_path = os.path.join(output_dir, f"{viz_id}.html")

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Visualization not found: {viz_id}"
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Visualization not found: {str(e)}"
        )

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
