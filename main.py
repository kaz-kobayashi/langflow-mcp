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
4. **CRITICAL: When user asks follow-up questions about optimization, ALWAYS check the conversation history to determine which policy type was used**
5. **TRIGGER WORDS FOR OPTIMIZATION**: When user says "より良い" (better), "最適化" (optimize), "探して" (find/search), "最適値" (optimal value), YOU MUST:
   - Look back in conversation history for the last simulation function called
   - Extract all parameters from that simulation
   - Call the corresponding optimization function immediately
   - DO NOT ask user for parameters again - extract them from history

あなたは在庫最適化の専門アシスタントです。以下のルールに従ってください：

**重要: ユーザーからパラメータが提供された場合は、必ず対応するツール（function）を呼び出してください。手動で計算しないでください。**

1. 利用可能なツール（function calling）がある場合は、必ずそれを使用してください
2. **在庫方策タイプの区別（最重要）**：
   - **(Q,R)方策（連続監視型・定量発注）**: 在庫がR以下になったら一定量Qを発注
     * シミュレーション → simulate_qr_policy
     * 最適化 → optimize_qr_policy
     * パラメータ: Q（発注量）、R（発注点）
   - **(s,S)方策（連続監視型・不定量発注）**: 在庫がs以下になったらSまで補充
     * シミュレーション → simulate_ss_policy
     * 最適化 → optimize_ss_policy
     * パラメータ: s（発注点）、S（基在庫レベル）
   - **定期発注方策（periodic review）**: サプライチェーンネットワーク全体の最適化
     * 最適化のみ → optimize_periodic_inventory
     * パラメータ: network_data（stages, connections, demand_dist）
   - **重要**: ユーザーが「より良いパラメータ」「最適化」を要求した場合、**必ず会話履歴を確認して、直前に使用した方策タイプと同じツールを選択してください**
     * 例: simulate_qr_policy実行後 → optimize_qr_policy を使用（optimize_periodic_inventoryは使用しない）
     * 例: simulate_ss_policy実行後 → optimize_ss_policy を使用
   - **パラメータの再利用**: フォローアップ質問では、会話履歴から前回使用したパラメータ（mu, sigma, lead_time, holding_cost, stockout_cost, fixed_costなど）を抽出して、最適化ツールに渡してください
     * ユーザーがパラメータを再入力する必要はありません
     * 例: 会話履歴で「mu: 100, sigma: 15, lead_time: 5, holding_cost: 1.0, stockout_cost: 100, fixed_cost: 500」が使われた場合、同じ値をoptimize_qr_policyに渡す
   - **具体的な会話フロー例**:
     ```
     ユーザー: (Q,R)シミュレーションを実行してください（パラメータ指定）
     AI: [simulate_qr_policyを実行] → 結果を説明

     ユーザー: より良いQとRを探してください
     AI: [会話履歴からmu, sigma, lead_time, holding_cost, stockout_cost, fixed_costを抽出]
         → optimize_qr_policy(mu=100, sigma=15, lead_time=5, holding_cost=1.0, stockout_cost=100, fixed_cost=500)を実行

     ユーザー: (s,S)シミュレーションを実行してください（パラメータ指定）
     AI: [simulate_ss_policyを実行] → 結果を説明

     ユーザー: より良いsとSを探してください
     AI: [会話履歴からmu, sigma, lead_time, holding_cost, stockout_cost, fixed_costを抽出]
         → optimize_ss_policy(mu=100, sigma=15, lead_time=5, holding_cost=1.0, stockout_cost=100, fixed_cost=500)を実行
     ```

3. 各ツールの使い分け：
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
5. 重要：定期発注最適化のツール選択：
   - **Adamアルゴリズム**（beta1, beta2パラメータ）を使う場合 → **optimize_periodic_inventory**（algorithm="adam"）を使用
   - **Momentumアルゴリズム**（momentumパラメータ）を使う場合 → **optimize_periodic_inventory**（algorithm="momentum"）を使用
   - **SGD（確率的勾配降下法）**を使う場合 → **optimize_periodic_inventory**（algorithm="sgd"）を使用
   - **Fit One Cycleスケジューラ**を使う場合 → optimize_periodic_with_one_cycle を使用
6. 重要：定期発注最適化（optimize_periodic_inventory）のパラメータ指定：
   - algorithmパラメータで最適化アルゴリズムを指定：
     * "adam": Adamアルゴリズム（beta1, beta2が必要）
     * "momentum": Momentumアルゴリズム（momentumパラメータが必要）
     * "sgd": 確率的勾配降下法（追加パラメータ不要）
   - 段階ごとに異なる値（例: 在庫保管費用: [0.5, 1.0, 2.0, 5.0]）が指定された場合：
     * 各段階のhフィールドに配列の対応する値を設定してください（Stage0はh=0.5, Stage1はh=1.0など）
   - 全段階共通の値（例: バックオーダーコスト: 100）が指定された場合：
     * トップレベルのbackorder_costパラメータに設定してください（各段階のbフィールドは省略可能）
   - リードタイムが配列で指定された場合（例: [3, 2, 2, 1]）：
     * 各段階のnet_replenishment_timeフィールドに配列の対応する値を設定してください
7. 重要：ユーザーが「可視化したい」「グラフを見たい」と要求した場合：
   - **EOQの可視化**：EOQ計算（calculate_eoq_*_raw）を実行した直後に visualize_eoq を呼び出す
   - **安全在庫ネットワークの可視化**：optimize_safety_stock_allocation で最適化を実行した後に visualize_last_optimization で可視化
   - **需要ヒストグラムの可視化**：visualize_demand_histogram（ヒストグラム+フィット分布）または find_best_distribution（80以上の分布から最適フィッティング）を使用
   - **シミュレーション軌道の可視化**：マルチステージシミュレーション後に visualize_simulation_trajectories で在庫レベルの時系列変化を表示
   - **サプライチェーンネットワークの可視化**：visualize_supply_chain_network で品目とBOMの関係をグラフ表示
   - calculate_safety_stock（単一品目）の結果は可視化できません
8. Pythonコードやmatplotlibのコードを絶対に生成しないでください
9. ツールで実行できる処理を独自に実装しないでください
10. 複数品目のデータがある場合や、BOM（部品表）が関係する場合は必ず optimize_safety_stock_allocation を使用してください
11. **最重要ルール**: 可視化ツール（visualize_eoq, visualize_last_optimization, find_best_distribution, visualize_demand_histogram, visualize_simulation_trajectories, visualize_supply_chain_network, visualize_forecast, visualize_periodic_optimization, visualize_safety_stock_network）の応答について：
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
                print(f"[CHAT DEBUG] No function call - Direct response")
                print(f"[CHAT DEBUG] Content: {assistant_content[:200] if assistant_content else 'None or empty'}")
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
        # まずファイルシステムから可視化HTMLを読み込む
        output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
        file_path = os.path.join(output_dir, f"{viz_id}.html")

        print(f"[VIZ DEBUG] Looking for visualization {viz_id}")
        print(f"[VIZ DEBUG] File path: {file_path}")
        print(f"[VIZ DEBUG] File exists: {os.path.exists(file_path)}")

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            print(f"[VIZ DEBUG] Visualization found in file system: {viz_id}")
            return HTMLResponse(content=html_content)

        # ファイルが見つからない場合、キャッシュから探す
        from mcp_tools import _optimization_cache

        print(f"[VIZ DEBUG] Number of users in cache: {len(_optimization_cache)}")

        # 全ユーザーのキャッシュから探す
        for user_id, cache in _optimization_cache.items():
            print(f"[VIZ DEBUG] Checking cache for user {user_id}: {len(cache)} items")
            if viz_id in cache:
                html_content = cache[viz_id]
                print(f"[VIZ DEBUG] Visualization found in cache for user {user_id}: {viz_id}")
                return HTMLResponse(content=html_content)

        # どこにも見つからない場合
        print(f"[VIZ DEBUG] Visualization not found anywhere: {viz_id}")
        print(f"[VIZ DEBUG] Available users in cache: {list(_optimization_cache.keys())}")
        raise HTTPException(
            status_code=404,
            detail=f"Visualization not found: {viz_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Visualization not found: {str(e)}"
        )

# ============================================================
# Direct MCP Tools API (JWT認証必須)
# ============================================================

@app.get("/api/tools")
async def list_tools(current_user: User = Depends(get_current_user)):
    """
    利用可能なMCPツール一覧を取得

    **認証**: JWT Bearer Token必須

    **レスポンス**:
    ```json
    {
        "tools": [
            {
                "name": "calculate_eoq_raw",
                "description": "基本的な経済発注量（EOQ）を計算",
                "parameters": {...}
            },
            ...
        ],
        "total": 32
    }
    ```
    """
    tools = []
    for tool in MCP_TOOLS_DEFINITION:
        tools.append({
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "parameters": tool["function"]["parameters"]
        })

    return {
        "tools": tools,
        "total": len(tools),
        "user": current_user.username
    }

@app.post("/api/tools/{tool_name}")
async def call_mcp_tool(
    tool_name: str,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    MCP Toolを直接呼び出す

    **認証**: JWT Bearer Token必須

    **パラメータ**:
    - `tool_name`: ツール名（例: calculate_eoq_raw, optimize_qr_policy）
    - `request`: ツールの入力パラメータ（JSON）

    **使用例**:
    ```bash
    curl -X POST https://your-app.railway.app/api/tools/calculate_eoq_raw \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
      -d '{
        "annual_demand": 15000,
        "order_cost": 500.0,
        "holding_cost_rate": 0.25,
        "unit_price": 12.0
      }'
    ```

    **レスポンス**:
    ```json
    {
        "success": true,
        "eoq_units": 1000,
        "total_cost": 3000.0,
        ...
    }
    ```
    """
    try:
        # ツールが存在するか確認
        available_tools = [tool["function"]["name"] for tool in MCP_TOOLS_DEFINITION]
        if tool_name not in available_tools:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found. Available tools: {', '.join(available_tools)}"
            )

        # MCP関数を実行
        result = execute_mcp_function(tool_name, request, user_id=current_user.id)

        # 結果にメタ情報を追加
        result["_meta"] = {
            "tool_name": tool_name,
            "user_id": current_user.id,
            "username": current_user.username
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error executing tool '{tool_name}': {str(e)}"
        )

# ============================================================
# Admin Token Management (管理者用トークン管理)
# ============================================================

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # 本番環境では必ず変更してください

def verify_admin_password(password: str = None):
    """管理者パスワードを検証"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=403,
            detail="Invalid admin password"
        )

@app.get("/admin/tokens", response_class=HTMLResponse)
async def admin_tokens_page(
    request: Request,
    password: str = None
):
    """
    管理者用トークン管理ページ

    **アクセス**: ?password=ADMIN_PASSWORD でアクセス

    例: http://localhost:8000/admin/tokens?password=admin123
    """
    # 簡易パスワード認証（本番環境では適切な認証システムを推奨）
    if not password or password != ADMIN_PASSWORD:
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>管理者ログイン</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-100 flex items-center justify-center min-h-screen">
                <div class="bg-white rounded-lg shadow-lg p-8 w-full max-w-md">
                    <h1 class="text-2xl font-bold text-gray-800 mb-6">🔐 管理者ログイン</h1>
                    <form method="GET" class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">管理者パスワード</label>
                            <input type="password" name="password" required
                                   class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent">
                        </div>
                        <button type="submit"
                                class="w-full px-4 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors">
                            ログイン
                        </button>
                    </form>
                    <p class="text-xs text-gray-500 mt-4">※環境変数 ADMIN_PASSWORD で設定されたパスワードを入力してください</p>
                </div>
            </body>
            </html>
            """,
            status_code=401
        )

    return templates.TemplateResponse("admin_tokens.html", {"request": request})

@app.get("/api/admin/users")
async def list_all_users(
    password: str = None,
    db: Session = Depends(get_db)
):
    """
    登録済みユーザー一覧を取得（管理者用）

    **認証**: クエリパラメータで管理者パスワードが必要

    例: GET /api/admin/users?password=admin123
    """
    verify_admin_password(password)

    users = db.query(User).order_by(User.id.desc()).all()

    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at.isoformat()
            }
            for user in users
        ],
        "total": len(users),
        "tokens_issued": len(users)  # トークン発行数（ユーザー数と同じ）
    }

class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    admin_password: str = None

@app.post("/api/admin/users")
async def admin_create_user(
    user: AdminUserCreate,
    db: Session = Depends(get_db)
):
    """
    新規ユーザーを作成してトークンを発行（管理者用）

    **認証**: リクエストボディに admin_password が必要
    """
    verify_admin_password(user.admin_password)

    # 重複チェック
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # ユーザー作成
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # トークン生成
    token = create_access_token(data={"sub": str(db_user.id)})

    return {
        "success": True,
        "user_id": db_user.id,
        "username": db_user.username,
        "email": db_user.email,
        "token": token,
        "token_type": "bearer",
        "expires_in_days": 7
    }

@app.post("/api/admin/users/{user_id}/reissue-token")
async def admin_reissue_token(
    user_id: int,
    password: str = None,
    db: Session = Depends(get_db)
):
    """
    既存ユーザーのトークンを再発行（管理者用）

    **認証**: クエリパラメータで管理者パスワードが必要

    例: POST /api/admin/users/3/reissue-token?password=admin123
    """
    verify_admin_password(password)

    # ユーザー取得
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # トークン生成
    token = create_access_token(data={"sub": str(user.id)})

    return {
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "token": token,
        "token_type": "bearer",
        "expires_in_days": 7
    }

# ============================================================
# Health Check
# ============================================================

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
