from fastapi import FastAPI, Request, Depends, HTTPException, status, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import re
from io import BytesIO
from openpyxl import load_workbook

from database import get_db, init_db, User, ChatHistory
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_optional
)
from mcp_tools import MCP_TOOLS_DEFINITION, execute_mcp_function, get_visualization_html
from scmopt2.optinv import make_excel_messa, prepare_opt_for_messa, solve_SSA

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

# ============================================================
# Pydantic Parameter Models for LLM Extraction
# ============================================================

class SafetyStockParams(BaseModel):
    """安全在庫計算のパラメータモデル"""
    mu: float = Field(..., description="平均需要（個/日）", gt=0)
    sigma: float = Field(..., description="需要の標準偏差", ge=0)
    lead_time: int = Field(..., description="リードタイム（日）", gt=0, alias="LT")
    service_level: Optional[float] = Field(None, description="サービスレベル（0-1）", ge=0, le=1)
    stockout_cost: Optional[float] = Field(None, description="品切れコスト（円/個）", ge=0, alias="b")
    holding_cost: Optional[float] = Field(None, description="在庫保管費用（円/個/日）", ge=0, alias="h")

    class Config:
        allow_population_by_field_name = True

    @validator('stockout_cost', 'holding_cost', always=True)
    def check_calculation_method(cls, v, values):
        """service_level または (stockout_cost と holding_cost) のいずれかが必須"""
        service_level = values.get('service_level')
        stockout_cost = values.get('stockout_cost')
        holding_cost = values.get('holding_cost')

        # service_levelが指定されている場合はOK
        if service_level is not None:
            return v

        # service_levelがない場合、stockout_costとholding_costが両方必要
        if v is None and (stockout_cost is None or holding_cost is None):
            raise ValueError("service_level または (stockout_cost と holding_cost) のいずれかを指定してください")

        return v

class EOQParams(BaseModel):
    """EOQ計算のパラメータモデル"""
    annual_demand: float = Field(..., description="年間需要（個/年）", gt=0, alias="D")
    order_cost: float = Field(..., description="発注費用（円/回）", gt=0, alias="K")
    holding_cost_rate: float = Field(..., description="在庫保管費率（年率）", gt=0, ge=0, le=1, alias="h")
    unit_price: float = Field(..., description="単価（円/個）", gt=0, alias="c")

    class Config:
        allow_population_by_field_name = True

class QRPolicyParams(BaseModel):
    """(Q,R)方策最適化/シミュレーションのパラメータモデル"""
    mu: float = Field(..., description="1日あたりの平均需要量（units/日）", gt=0)
    sigma: float = Field(..., description="需要の標準偏差", ge=0)
    lead_time: int = Field(..., description="リードタイム（日）", gt=0)
    holding_cost: float = Field(..., description="在庫保管費用（円/unit/日）", gt=0)
    stockout_cost: float = Field(..., description="品切れ費用（円/unit）", gt=0)
    fixed_cost: float = Field(..., description="固定発注費用（円/回）", gt=0)
    # シミュレーション用オプションパラメータ
    Q: Optional[float] = Field(None, description="発注量（units）- シミュレーション時のみ必須", gt=0)
    R: Optional[float] = Field(None, description="発注点（units）- シミュレーション時のみ必須", gt=0)
    n_samples: Optional[int] = Field(10, description="シミュレーションサンプル数", gt=0)
    n_periods: Optional[int] = Field(100, description="シミュレーション期間（日）", gt=0)

    class Config:
        allow_population_by_field_name = True

class SSPolicyParams(BaseModel):
    """(s,S)方策最適化/シミュレーションのパラメータモデル"""
    mu: float = Field(..., description="1日あたりの平均需要量（units/日）", gt=0)
    sigma: float = Field(..., description="需要の標準偏差", ge=0)
    lead_time: int = Field(..., description="リードタイム（日）", gt=0)
    holding_cost: float = Field(..., description="在庫保管費用（円/unit/日）", gt=0)
    stockout_cost: float = Field(..., description="品切れ費用（円/unit）", gt=0)
    fixed_cost: float = Field(..., description="固定発注費用（円/回）", gt=0)
    # シミュレーション用オプションパラメータ
    s: Optional[float] = Field(None, description="発注点（units）- シミュレーション時のみ必須", gt=0)
    S: Optional[float] = Field(None, description="基在庫レベル（units）- シミュレーション時のみ必須", gt=0)
    n_samples: Optional[int] = Field(10, description="シミュレーションサンプル数", gt=0)
    n_periods: Optional[int] = Field(100, description="シミュレーション期間（日）", gt=0)

    class Config:
        allow_population_by_field_name = True

class DemandForecastParams(BaseModel):
    """需要予測のパラメータモデル"""
    demand_history: List[float] = Field(..., description="過去の需要データ配列", min_items=2)
    forecast_periods: Optional[int] = Field(7, description="予測する期間数", gt=0)
    method: Optional[str] = Field("exponential_smoothing", description="予測手法: moving_average, exponential_smoothing, linear_trend")
    confidence_level: Optional[float] = Field(0.95, description="信頼水準（0-1）", ge=0, le=1)
    window: Optional[int] = Field(None, description="移動平均法の窓サイズ（moving_averageの場合のみ）", gt=0)
    alpha: Optional[float] = Field(0.3, description="指数平滑法の平滑化パラメータ（0-1）", ge=0, le=1)
    visualize: Optional[bool] = Field(False, description="予測結果を可視化するかどうか")

    class Config:
        allow_population_by_field_name = True

    @validator('method')
    def validate_method(cls, v):
        """予測手法の検証"""
        allowed_methods = ["moving_average", "exponential_smoothing", "linear_trend"]
        if v not in allowed_methods:
            raise ValueError(f"method must be one of {allowed_methods}, got '{v}'")
        return v

class DemandAnalysisParams(BaseModel):
    """需要パターン分析のパラメータモデル"""
    demand: List[float] = Field(..., description="需要データの配列", min_items=1)

    class Config:
        allow_population_by_field_name = True

class WagnerWhitinParams(BaseModel):
    """Wagner-Whitinアルゴリズムのパラメータモデル"""
    demand: List[float] = Field(..., description="各期の需要量の配列", min_items=1)
    fixed_cost: float = Field(..., description="固定発注費用（円/回）", gt=0)
    holding_cost: float = Field(..., description="在庫保管費用（円/unit/期）", ge=0)
    variable_cost: Optional[float] = Field(0, description="変動発注費用（円/unit）", ge=0)

    class Config:
        allow_population_by_field_name = True

class DistributionFittingParams(BaseModel):
    """最適分布フィッティングのパラメータモデル"""
    demand: List[float] = Field(..., description="需要データの配列", min_items=1)

    class Config:
        allow_population_by_field_name = True

class HistogramFittingParams(BaseModel):
    """ヒストグラム分布フィッティングのパラメータモデル"""
    demand_data: List[float] = Field(..., description="需要データの配列", min_items=1)
    nbins: Optional[int] = Field(50, description="ヒストグラムのビン数", gt=0)

    class Config:
        allow_population_by_field_name = True

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
# Automatic Tool Detection with LLM
# ============================================================

class ToolDetectionRequest(BaseModel):
    user_text: str

@app.post("/api/detect_tool")
async def detect_tool(
    request: ToolDetectionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    ユーザーのテキスト入力から適切なツールを自動検出する

    **認証**: オプション（ローカル環境では不要）

    **使用例**:
    ```bash
    curl -X POST http://localhost:8000/api/detect_tool \
      -H "Content-Type: application/json" \
      -d '{"user_text": "平均需要100個で(Q,R)方策を最適化したい"}'
    ```

    **レスポンス例（成功）**:
    ```json
    {
        "success": true,
        "detected_tools": [
            {
                "tool_name": "optimize_qr_policy",
                "confidence": 0.95,
                "description": "(Q,R)方策の最適パラメータを計算します",
                "required_params": ["mu", "sigma", "lead_time", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        ],
        "recommended_tool": "optimize_qr_policy"
    }
    ```
    """

    # 全ツールのリストと説明を取得
    tools_summary = []
    for tool in MCP_TOOLS_DEFINITION:
        tool_info = {
            "name": tool["function"]["name"],
            "description": tool["function"]["description"],
            "required_params": tool["function"]["parameters"].get("required", [])
        }
        tools_summary.append(tool_info)

    # LLMにツール検出を依頼
    detection_prompt = f"""
以下のユーザー入力から、最も適切な在庫最適化ツールを検出してください。

【利用可能なツール一覧】
{json.dumps(tools_summary, indent=2, ensure_ascii=False)}

【ユーザー入力】
{request.user_text}

【検出ルール】
1. ユーザーの意図を理解し、最も適したツールを1-3個選択してください
2. 各ツールに対して信頼度スコア（0-1）を付けてください
3. キーワードマッチング例：
   - "EOQ", "経済発注量", "発注量" → calculate_eoq_raw または calculate_eoq_*_discount_raw
   - "安全在庫", "サービスレベル" → calculate_safety_stock
   - "(Q,R)", "定量発注", "連続監視" → optimize_qr_policy または simulate_qr_policy
   - "(s,S)", "不定量発注", "基在庫" → optimize_ss_policy または simulate_ss_policy
   - "需要予測", "予測", "forecast" → forecast_demand
   - "需要分析", "統計", "パターン" → analyze_demand_pattern
   - "Wagner-Whitin", "動的ロットサイジング" → calculate_wagner_whitin
   - "定期発注", "periodic review", "ネットワーク最適化" → optimize_periodic_inventory
   - "最適化", "optimize" → 対応する最適化ツール（optimize_qr_policy, optimize_ss_policy など）
   - "シミュレーション", "simulate" → 対応するシミュレーションツール（simulate_qr_policy, simulate_ss_policy など）

【出力形式】
以下のJSON形式で出力してください：
```json
{{
  "detected_tools": [
    {{
      "tool_name": "ツール名",
      "confidence": 0.95,
      "reason": "このツールを選んだ理由"
    }}
  ],
  "recommended_tool": "最も推奨されるツール名"
}}
```
"""

    try:
        # OpenAI API呼び出し
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            messages=[
                {"role": "system", "content": "あなたは在庫最適化ツールの選択を支援する専門家です。ユーザーの入力から最適なツールを検出してください。"},
                {"role": "user", "content": detection_prompt}
            ],
            temperature=0.0,
            max_tokens=1024,
        )

        response_text = response.choices[0].message.content

        # JSONを抽出
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(1)
        else:
            extracted_json = response_text.strip()

        detection_result = json.loads(extracted_json)

        # 検出されたツールの詳細情報を追加
        detected_tools_with_details = []
        for detected in detection_result.get("detected_tools", []):
            tool_name = detected["tool_name"]

            # ツール定義から詳細情報を取得
            tool_def = next((t for t in MCP_TOOLS_DEFINITION if t["function"]["name"] == tool_name), None)
            if tool_def:
                detected_tools_with_details.append({
                    "tool_name": tool_name,
                    "confidence": detected.get("confidence", 0.5),
                    "reason": detected.get("reason", ""),
                    "description": tool_def["function"]["description"],
                    "required_params": tool_def["function"]["parameters"].get("required", [])
                })

        return {
            "success": True,
            "detected_tools": detected_tools_with_details,
            "recommended_tool": detection_result.get("recommended_tool"),
            "user_text": request.user_text
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "LLMからのJSON抽出に失敗しました",
            "details": str(e),
            "llm_response": response_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": "ツール検出に失敗しました",
            "details": str(e)
        }

# ============================================================
# Parameter Extraction with LLM (Pydantic-based)
# ============================================================

class ParameterExtractionRequest(BaseModel):
    tool_name: str
    user_text: str

@app.post("/api/extract_parameters")
async def extract_parameters(
    request: ParameterExtractionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    ユーザーのテキスト入力からLLMを使ってパラメータを抽出し、
    Pydanticモデルでバリデーションする

    **認証**: オプション（ローカル環境では不要）

    **使用例**:
    ```bash
    curl -X POST http://localhost:8000/api/extract_parameters \
      -H "Content-Type: application/json" \
      -d '{
        "tool_name": "calculate_safety_stock",
        "user_text": "平均需要100個/日、標準偏差20、リードタイム7日、サービスレベル95%の場合の安全在庫を計算してください"
      }'
    ```

    **レスポンス例（成功）**:
    ```json
    {
        "success": true,
        "parameters": {
            "mu": 100.0,
            "sigma": 20.0,
            "lead_time": 7,
            "service_level": 0.95
        },
        "schema": {...}
    }
    ```

    **レスポンス例（失敗）**:
    ```json
    {
        "success": false,
        "error": "パラメータのバリデーションに失敗しました",
        "details": "service_level または (stockout_cost と holding_cost) のいずれかを指定してください",
        "extracted_params": {...},
        "schema": {...}
    }
    ```
    """

    # ツールに対応するPydanticモデルを取得
    param_models: Dict[str, Any] = {
        # EOQ
        "calculate_eoq_raw": EOQParams,
        # 安全在庫
        "calculate_safety_stock": SafetyStockParams,
        # (Q,R)方策
        "optimize_qr_policy": QRPolicyParams,
        "simulate_qr_policy": QRPolicyParams,
        # (s,S)方策
        "optimize_ss_policy": SSPolicyParams,
        "simulate_ss_policy": SSPolicyParams,
        # 需要予測
        "forecast_demand": DemandForecastParams,
        # 需要分析
        "analyze_demand_pattern": DemandAnalysisParams,
        # 分布フィッティング
        "find_best_distribution": DistributionFittingParams,
        "fit_histogram_distribution": HistogramFittingParams,
        # Wagner-Whitin
        "calculate_wagner_whitin": WagnerWhitinParams,
    }

    if request.tool_name not in param_models:
        raise HTTPException(
            status_code=400,
            detail=f"Tool '{request.tool_name}' does not support parameter extraction. Supported tools: {', '.join(param_models.keys())}"
        )

    model_class = param_models[request.tool_name]

    # Pydanticモデルのスキーマを取得
    schema = model_class.schema()

    # LLMにパラメータ抽出を依頼
    extraction_prompt = f"""
以下のユーザー入力から、{request.tool_name} 関数に必要なパラメータを抽出してJSON形式で出力してください。

【関数パラメータスキーマ】
{json.dumps(schema, indent=2, ensure_ascii=False)}

【ユーザー入力】
{request.user_text}

【重要な抽出ルール】
1. 出力はJSON形式のみで、説明文は不要です
2. スキーマに定義された型と制約に従ってください
3. 数値の単位に注意：
   - サービスレベルは0-1の範囲（例：95% → 0.95）
   - パーセントが指定された場合は小数に変換してください
4. aliasが定義されている場合は、どちらの名前でも受け付けます（例：lead_time または LT）
5. 不足しているパラメータがある場合は、その旨をerrorフィールドに記載してください

【出力形式】
以下のJSON形式でのみ出力してください：
```json
{{
  "パラメータ名": 値,
  ...
}}
```

エラーがある場合のみ、以下の形式：
```json
{{
  "error": "エラーメッセージ"
}}
```
"""

    try:
        # OpenAI API呼び出し（既存のclientインスタンスを使用）
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            messages=[
                {"role": "system", "content": "あなたはテキストからパラメータを抽出する専門家です。指示に従ってJSONのみを出力してください。"},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.0,  # 一貫性のため低温度
            max_tokens=1024,
        )

        response_text = response.choices[0].message.content

        # LLMの出力からJSONを抽出
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            extracted_json = json_match.group(1)
        else:
            # コードブロックがない場合、全体をJSONとして扱う
            extracted_json = response_text.strip()

        extracted_params = json.loads(extracted_json)

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": "LLMからのJSON抽出に失敗しました",
            "details": str(e),
            "llm_response": response_text,
            "schema": schema
        }
    except Exception as e:
        return {
            "success": False,
            "error": "LLM呼び出しに失敗しました",
            "details": str(e),
            "schema": schema
        }

    # エラーフィールドがある場合、抽出失敗として扱う
    if "error" in extracted_params:
        return {
            "success": False,
            "error": "パラメータの抽出に失敗しました",
            "details": extracted_params["error"],
            "schema": schema
        }

    # Pydanticモデルでバリデーション
    try:
        validated_model = model_class(**extracted_params)
        # by_aliasを使用してエイリアス名でシリアライズ
        validated_params = validated_model.dict(by_alias=True)

        return {
            "success": True,
            "parameters": validated_params,
            "extracted_params": extracted_params,  # 抽出前のパラメータも参考情報として返す
            "schema": schema,
            "message": "パラメータの抽出とバリデーションに成功しました"
        }

    except Exception as e:
        # バリデーションエラー詳細を返す
        error_details = str(e)

        # Pydantic V1 ValidationErrorの場合
        if hasattr(e, 'errors'):
            error_details = json.dumps(e.errors(), ensure_ascii=False, indent=2)

        return {
            "success": False,
            "error": "パラメータのバリデーションに失敗しました",
            "details": error_details,
            "extracted_params": extracted_params,
            "schema": schema,
            "suggestion": "スキーマを確認して、必須パラメータが全て含まれているか、値の範囲が正しいかをチェックしてください"
        }

# ============================================================
# MESSA Excel Template功能 (Download/Upload)
# ============================================================

@app.get("/api/download_messa_template")
async def download_messa_template(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    MESSAの Excelテンプレートをダウンロード

    **認証**: オプション（ローカル環境では不要）

    **使用方法**:
    1. このエンドポイントからテンプレートをダウンロード
    2. Excelで品目データとBOMデータを入力
    3. /api/upload_messa_excel にアップロードして最適化実行

    **テンプレート構造**:
    - 品目シート: 品目名、処理時間、最大サービス時間、平均需要、需要標準偏差、在庫保管費用、品切れ費用、固定発注費用
    - 部品展開表シート: 子品目、親品目、数量
    """
    try:
        # Excelテンプレートを生成
        wb = make_excel_messa()

        # BytesIOに保存
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        # Excelファイルとしてダウンロード
        headers = {
            'Content-Disposition': 'attachment; filename="messa_template.xlsx"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }

        return Response(
            content=excel_buffer.getvalue(),
            headers=headers,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Excelテンプレート生成に失敗しました: {str(e)}"
        )


@app.post("/api/upload_messa_excel")
async def upload_messa_excel(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    MESSAのExcelファイルをアップロードして最適化を実行

    **認証**: オプション（ローカル環境では不要）

    **使用方法**:
    1. /api/download_messa_template からテンプレートをダウンロード
    2. Excelで品目データとBOMデータを入力
    3. このエンドポイントにアップロード

    **レスポンス例**:
    ```json
    {
        "status": "success",
        "optimization_results": [
            {
                "node": "製品A",
                "safety_stock": 50.5,
                "service_time": 3.0,
                "lead_time": 1.0
            }
        ],
        "total_cost": 12345.67
    }
    ```
    """
    try:
        # アップロードされたファイルを読み込む
        contents = await file.read()
        excel_buffer = BytesIO(contents)

        # Excelファイルを読み込む
        wb = load_workbook(excel_buffer)

        # ネットワークグラフを構築
        G = prepare_opt_for_messa(wb)

        # 最適化実行
        best_sol = solve_SSA(G)

        # 結果を整形
        result_data = []
        for idx, node in enumerate(G.nodes()):
            result_data.append({
                "node": node,
                "safety_stock": float(best_sol["best_NRT"][idx]),
                "service_time": float(best_sol["best_MaxLI"][idx]),
                "lead_time": float(best_sol["best_MinLT"][idx])
            })

        return {
            "status": "success",
            "optimization_results": result_data,
            "total_cost": float(best_sol.get("best_cost", 0)),
            "message": "最適化が正常に完了しました"
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Excelファイルの処理または最適化に失敗しました: {str(e)}"
        )


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
