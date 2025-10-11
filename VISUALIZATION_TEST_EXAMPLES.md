# 可視化ツール 網羅的テスト入力例

**作成日**: 2025-10-11
**目的**: 全可視化ツールのテスト用入力例を提供

---

## 📊 可視化ツール一覧（10ツール）

| # | ツール名 | 可視化内容 | 事前実行が必要なツール |
|---|---------|-----------|---------------------|
| 1 | visualize_last_optimization | 安全在庫配置ネットワーク | optimize_safety_stock_allocation |
| 2 | visualize_inventory_simulation | 在庫シミュレーション軌道 | なし |
| 3 | visualize_demand_histogram | 需要ヒストグラム | なし |
| 4 | compare_inventory_costs_visual | 在庫方策コスト比較 | なし |
| 5 | visualize_forecast | 需要予測グラフ | なし |
| 6 | visualize_periodic_optimization | 定期発注最適化学習曲線 | optimize_periodic_inventory |
| 7 | visualize_safety_stock_network | 安全在庫ネットワーク | optimize_safety_stock_allocation |
| 8 | visualize_eoq | EOQ総コスト曲線 | calculate_eoq_*_raw |
| 9 | visualize_simulation_trajectories | マルチステージシミュレーション軌道 | simulate_multistage_* |
| 10 | visualize_supply_chain_network | サプライチェーンネットワーク構造 | なし |

---

## 1. visualize_last_optimization

**目的**: 直前に実行した安全在庫最適化結果の可視化

**使用方法**:
1. まず `optimize_safety_stock_allocation` を実行
2. その後このツールを実行（パラメータ不要）

**入力例**:
```
3段階サプライチェーンの安全在庫配置を最適化して、結果を可視化してください。

品目データ:
[
  {"name": "原材料", "h": 1.0, "b": 50.0, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0, "echelon_lead_time": 5.0},
  {"name": "中間品", "h": 2.0, "b": 100.0, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0, "echelon_lead_time": 3.0},
  {"name": "最終製品", "h": 5.0, "b": 150.0, "avg_demand": 100.0, "demand_std": 20.0, "lead_time": 1.0, "echelon_lead_time": 1.0}
]

BOMデータ:
[
  {"child": "原材料", "parent": "中間品", "units": 1.0},
  {"child": "中間品", "parent": "最終製品", "units": 1.0}
]

z値: 1.65

その後、結果を可視化してください。
```

**期待される出力**:
- ネットワーク図（ノードサイズ = NRT、色 = 保証リードタイム）
- 各ノードの安全在庫レベル
- 総コスト

---

## 2. visualize_inventory_simulation

**目的**: 在庫方策のシミュレーション軌道を可視化

**入力例1（(Q,R)方策）**:
```
(Q,R)方策の在庫シミュレーションを可視化してください。

パラメータ:
- 平均需要: 100個/日
- 需要の標準偏差: 15個/日
- リードタイム: 5日
- 方策タイプ: QR
- 発注量Q: 200個
- 発注点R: 80個
- 在庫保管費用: 1円/個/日
- 品切れコスト: 100円/個
- 固定発注コスト: 500円
- シミュレーション期間: 100日
```

**入力例2（(s,S)方策）**:
```
(s,S)方策の在庫シミュレーションを可視化してください。

パラメータ:
- 平均需要: 100個/日
- 需要の標準偏差: 15個/日
- リードタイム: 5日
- 方策タイプ: sS
- 発注点s: 75個
- 基在庫レベルS: 225個
- 在庫保管費用: 1円/個/日
- 品切れコスト: 100円/個
- 固定発注コスト: 500円
- シミュレーション期間: 100日
```

**期待される出力**:
- 在庫レベルの時系列グラフ
- 発注タイミングマーカー
- 品切れ期間のハイライト
- 統計サマリー

---

## 3. visualize_demand_histogram

**目的**: 需要データのヒストグラムと統計量の可視化

**入力例1（基本）**:
```
以下の需要データのヒストグラムを作成してください。

需要データ:
[95, 102, 98, 105, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 135, 132, 140, 138, 145, 143, 150, 148, 155, 152, 160, 158, 165, 162, 170, 168]
```

**入力例2（ビン数指定）**:
```
以下の需要データのヒストグラムを20ビンで作成してください。

需要データ:
[85, 92, 88, 95, 100, 98, 105, 102, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 135, 132, 140, 138, 145, 143, 150, 148, 155, 152, 160, 158, 165, 162, 170, 168, 175, 172, 180, 178, 185, 182]

ビン数: 20
```

**期待される出力**:
- ヒストグラム
- 基本統計量（平均、標準偏差、中央値、最小値、最大値）
- フィットした正規分布曲線

---

## 4. compare_inventory_costs_visual

**目的**: EOQ、(Q,R)、(s,S)方策のコスト比較

**入力例**:
```
以下の条件で、EOQ、(Q,R)方策、(s,S)方策のコストを比較してください。

パラメータ:
- 平均需要: 100個/日
- 需要の標準偏差: 15個/日
- リードタイム: 5日
- 在庫保管費用: 1円/個/日
- 品切れコスト: 100円/個
- 固定発注コスト: 500円
- サンプル数: 30
- シミュレーション期間: 200日
```

**期待される出力**:
- 3つの方策の平均コスト棒グラフ
- 推奨方策
- コスト削減額

---

## 5. visualize_forecast

**目的**: 需要予測結果の時系列グラフ

**入力例1（移動平均法）**:
```
移動平均法で需要を予測し、可視化してください。

過去の需要データ:
[95, 102, 98, 105, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 135, 132, 140, 138, 145, 143]

予測期間: 10期
手法: moving_average
窓サイズ: 7
```

**入力例2（指数平滑法）**:
```
指数平滑法で需要を予測し、可視化してください。

過去の需要データ:
[85, 90, 88, 95, 100, 98, 105, 102, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 135, 132, 140, 138, 145, 143, 150]

予測期間: 7期
手法: exponential_smoothing
α: 0.3
信頼水準: 0.95
```

**入力例3（線形トレンド法）**:
```
線形トレンド法で需要を予測し、可視化してください。

過去の需要データ:
[50, 55, 58, 62, 67, 70, 75, 78, 82, 87, 90, 95, 98, 102, 107, 110, 115, 118, 122, 127]

予測期間: 10期
手法: linear_trend
```

**期待される出力**:
- 過去データの時系列プロット
- 予測値の時系列プロット
- 信頼区間（帯グラフ）
- 過去と未来の境界線

---

## 6. visualize_periodic_optimization

**目的**: 定期発注最適化の学習曲線

**使用方法**:
1. まず `optimize_periodic_inventory` を実行
2. その結果を引数として渡す

**入力例**:
```
3段階サプライチェーンの定期発注方策をAdamで最適化して、学習曲線を可視化してください。

ネットワークデータ:
{
  "stages": [
    {"name": "Stage0", "average_demand": 0, "sigma": 0, "h": 0.5, "b": 100, "capacity": 1000, "net_replenishment_time": 3},
    {"name": "Stage1", "average_demand": 0, "sigma": 0, "h": 1.0, "b": 100, "capacity": 1000, "net_replenishment_time": 2},
    {"name": "Stage2", "average_demand": 100, "sigma": 15, "h": 2.0, "b": 100, "capacity": 1000, "net_replenishment_time": 1}
  ],
  "connections": [
    {"child": "Stage0", "parent": "Stage1", "units": 1, "allocation": 1.0},
    {"child": "Stage1", "parent": "Stage2", "units": 1, "allocation": 1.0}
  ]
}

最大反復回数: 50
サンプル数: 20
シミュレーション期間: 100
アルゴリズム: adam
学習率: 0.1

その後、最適化結果を可視化してください。
```

**期待される出力**:
- コストの学習曲線
- 基在庫レベルの変化
- 収束状況

---

## 7. visualize_safety_stock_network

**目的**: 安全在庫配置ネットワークの可視化

**使用方法**:
1. まず `optimize_safety_stock_allocation` を実行
2. その結果を引数として渡す

**入力例**:
```
5段階ツリー構造の安全在庫配置を最適化して、ネットワーク図を表示してください。

品目データ:
[
  {"name": "Stage0", "h": 0.5, "b": 50.0, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0, "echelon_lead_time": 5.0},
  {"name": "Stage1", "h": 1.0, "b": 75.0, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0, "echelon_lead_time": 4.0},
  {"name": "Stage2", "h": 1.5, "b": 100.0, "avg_demand": 0, "demand_std": 0, "lead_time": 1.0, "echelon_lead_time": 3.0},
  {"name": "Stage3", "h": 2.0, "b": 125.0, "avg_demand": 0, "demand_std": 0, "lead_time": 1.0, "echelon_lead_time": 2.0},
  {"name": "Stage4", "h": 5.0, "b": 150.0, "avg_demand": 200.0, "demand_std": 30.0, "lead_time": 1.0, "echelon_lead_time": 1.0}
]

BOMデータ:
[
  {"child": "Stage0", "parent": "Stage1", "units": 1.0},
  {"child": "Stage1", "parent": "Stage2", "units": 1.0},
  {"child": "Stage2", "parent": "Stage3", "units": 1.0},
  {"child": "Stage3", "parent": "Stage4", "units": 1.0}
]

z値: 1.65

その後、ネットワーク図を可視化してください。
```

**期待される出力**:
- ネットワーク図（Plotly）
- ノードサイズ: 正味補充時間（NRT）
- ノード色: 保証リードタイム（Lstar）
- エッジ: BOM関係

---

## 8. visualize_eoq

**目的**: EOQ総コスト曲線の可視化

**使用方法**:
1. まず `calculate_eoq_raw`、`calculate_eoq_incremental_discount_raw`、または `calculate_eoq_all_units_discount_raw` を実行
2. その後このツールを実行（パラメータ不要）

**入力例1（基本EOQ）**:
```
基本EOQを計算して、総コスト曲線を可視化してください。

年間需要: 12000個
発注費用: 500円/回
在庫保管費率: 0.2（年率20%）
単価: 10円/個

その後、EOQを可視化してください。
```

**入力例2（バックオーダー対応EOQ）**:
```
バックオーダー対応EOQを計算して、総コスト曲線を可視化してください。

年間需要: 12000個
発注費用: 500円/回
在庫保管費率: 0.2
単価: 10円/個
バックオーダーコスト: 100円/個

その後、EOQを可視化してください。
```

**入力例3（増分数量割引）**:
```
増分数量割引のEOQを計算して、可視化してください。

年間需要: 10000個
発注費用: 1000円/回
在庫保管費率: 0.25
基本単価: 100円/個

数量割引（増分割引）:
- 500個以上: 5%割引
- 1000個以上: 8%割引
- 2000個以上: 12%割引

その後、EOQを可視化してください。
```

**入力例4（全単位数量割引）**:
```
全単位数量割引のEOQを計算して、可視化してください。

年間需要: 10000個
発注費用: 1000円/回
在庫保管費率: 0.25
基本単価: 100円/個

数量割引（全単位割引）:
- 500個以上: 単価95円
- 1000個以上: 単価90円
- 2000個以上: 単価85円

その後、EOQを可視化してください。
```

**期待される出力**:
- 総コスト曲線
- 最適発注量のマーカー
- 数量割引がある場合は割引境界も表示

---

## 9. visualize_simulation_trajectories

**目的**: マルチステージシミュレーションの在庫軌道可視化

**使用方法**:
1. マルチステージシミュレーションを実行（`simulate_multistage_inventory`、`simulate_base_stock_multistage`、または `simulate_multistage_fixed`）
2. その後このツールを実行

**入力例1（最後のシミュレーション結果を使用）**:
```
3段階サプライチェーンのマルチステージシミュレーションを実行してください。

ネットワークデータ:
{
  "stages": [
    {"name": "原材料", "average_demand": 0, "sigma": 0, "h": 0.5, "b": 100, "capacity": 1000, "net_replenishment_time": 3},
    {"name": "中間品", "average_demand": 0, "sigma": 0, "h": 1.0, "b": 100, "capacity": 1000, "net_replenishment_time": 2},
    {"name": "完成品", "average_demand": 100, "sigma": 15, "h": 2.0, "b": 100, "capacity": 1000, "net_replenishment_time": 1}
  ],
  "connections": [
    {"child": "原材料", "parent": "中間品", "units": 1, "allocation": 1.0},
    {"child": "中間品", "parent": "完成品", "units": 1, "allocation": 1.0}
  ]
}

基在庫レベル: [300, 200, 150]
サンプル数: 10
シミュレーション期間: 100

その後、シミュレーション軌道を可視化してください。

段階名: ["原材料", "中間品", "完成品"]
表示サンプル数: 5
```

**入力例2（データ直接指定）**:
```
以下の在庫データの軌道を可視化してください。

在庫データ: [3次元配列: samples × stages × periods]
段階名: ["原材料", "中間品", "完成品"]
表示期間: 50期
表示サンプル数: 3
表示段階: [0, 1, 2]
```

**期待される出力**:
- 各段階の在庫レベル時系列グラフ
- 複数サンプルの軌道を重ねて表示
- 段階ごとにサブプロット

---

## 10. visualize_supply_chain_network

**目的**: サプライチェーンネットワーク構造の可視化

**入力例1（シンプルな直列ネットワーク）**:
```
以下のサプライチェーンネットワークを可視化してください。

品目データ:
[
  {"name": "原材料", "h": 0.5, "avg_demand": 0, "demand_std": 0},
  {"name": "中間品", "h": 1.0, "avg_demand": 0, "demand_std": 0},
  {"name": "完成品", "h": 2.0, "avg_demand": 100, "demand_std": 15}
]

BOMデータ:
[
  {"child": "原材料", "parent": "中間品", "units": 1},
  {"child": "中間品", "parent": "完成品", "units": 1}
]
```

**入力例2（分岐のあるネットワーク）**:
```
以下のサプライチェーンネットワークを可視化してください。

品目データ:
[
  {"name": "原材料A", "h": 0.5, "avg_demand": 0, "demand_std": 0},
  {"name": "原材料B", "h": 0.8, "avg_demand": 0, "demand_std": 0},
  {"name": "原材料C", "h": 0.6, "avg_demand": 0, "demand_std": 0},
  {"name": "中間品1", "h": 2.0, "avg_demand": 0, "demand_std": 0},
  {"name": "中間品2", "h": 2.5, "avg_demand": 0, "demand_std": 0},
  {"name": "最終製品", "h": 5.0, "avg_demand": 1000, "demand_std": 150}
]

BOMデータ:
[
  {"child": "原材料A", "parent": "中間品1", "units": 1},
  {"child": "原材料B", "parent": "中間品1", "units": 2},
  {"child": "原材料C", "parent": "中間品2", "units": 1},
  {"child": "中間品1", "parent": "最終製品", "units": 1},
  {"child": "中間品2", "parent": "最終製品", "units": 1}
]
```

**入力例3（複雑なネットワーク）**:
```
以下の複雑なサプライチェーンネットワークを可視化してください。

品目データ:
[
  {"name": "原材料A", "h": 0.5, "avg_demand": 0, "demand_std": 0, "lead_time": 3.0},
  {"name": "原材料B", "h": 0.8, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0},
  {"name": "原材料C", "h": 0.6, "avg_demand": 0, "demand_std": 0, "lead_time": 4.0},
  {"name": "部品1", "h": 1.5, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0},
  {"name": "部品2", "h": 1.8, "avg_demand": 0, "demand_std": 0, "lead_time": 2.0},
  {"name": "部品3", "h": 2.0, "avg_demand": 0, "demand_std": 0, "lead_time": 1.0},
  {"name": "サブ組立1", "h": 3.0, "avg_demand": 0, "demand_std": 0, "lead_time": 1.0},
  {"name": "最終製品", "h": 5.0, "avg_demand": 500, "demand_std": 80, "lead_time": 1.0}
]

BOMデータ:
[
  {"child": "原材料A", "parent": "部品1", "units": 2},
  {"child": "原材料B", "parent": "部品1", "units": 1},
  {"child": "原材料B", "parent": "部品2", "units": 3},
  {"child": "原材料C", "parent": "部品3", "units": 1},
  {"child": "部品1", "parent": "サブ組立1", "units": 1},
  {"child": "部品2", "parent": "サブ組立1", "units": 1},
  {"child": "部品3", "parent": "最終製品", "units": 2},
  {"child": "サブ組立1", "parent": "最終製品", "units": 1}
]
```

**期待される出力**:
- ネットワークグラフ（Plotly）
- ノード: 品目
- エッジ: BOM関係（方向あり）
- ノード情報: 名前、保管費用、需要
- インタラクティブなズーム・パン機能

---

## 📋 テスト実行方法

### 方法1: OpenAI Function Calling経由（推奨）

Railway環境でOpenAI互換APIを使用してテスト：

```bash
# 環境変数を設定
export OPENAI_API_KEY="your-api-key"
# または
export OPENAI_BASE_URL="http://localhost:1234/v1"  # LM Studio使用時

# Railwayデプロイ後にテスト
# ユーザーとして上記の入力例を送信
```

### 方法2: ローカル直接呼び出し

```python
from mcp_tools import execute_mcp_function
import numpy as np

# 例: visualize_demand_histogram
demand_data = np.random.normal(100, 15, 100).tolist()
result = execute_mcp_function('visualize_demand_histogram', {
    'demand': demand_data,
    'nbins': 20
}, user_id='test_user')

print(f"Status: {result.get('status')}")
print(f"Visualization ID: {result.get('visualization_id')}")
print(f"URL: {result.get('visualization_url')}")
```

### 方法3: 自動テストスクリプト

```python
# test_visualizations.py を作成して実行
python test_visualizations.py
```

---

## ⚠️ 注意事項

### 可視化タイプ別の注意点

**タイプA: パラメータ不要（結果を再利用）**
- `visualize_last_optimization`
- `visualize_eoq`
- これらは事前に対応するツールを実行する必要があります

**タイプB: 最適化結果を引数で受け取る**
- `visualize_periodic_optimization`
- `visualize_safety_stock_network`
- これらは最適化ツールの結果オブジェクトを引数として渡す必要があります

**タイプC: キャッシュから取得可能**
- `visualize_simulation_trajectories`
- パラメータなしで実行すると最後のシミュレーション結果を使用します

**タイプD: 完全独立実行**
- `visualize_inventory_simulation`
- `visualize_demand_histogram`
- `compare_inventory_costs_visual`
- `visualize_forecast`
- `visualize_supply_chain_network`
- これらは事前実行不要で、直接パラメータを指定して実行できます

### 可視化結果の取得

すべての可視化ツールは以下の形式で結果を返します：

```json
{
  "status": "success",
  "visualization_type": "可視化タイプ名",
  "visualization_id": "uuid形式のID",
  "visualization_url": "可視化ページのURL（Railwayの場合）",
  ...
}
```

可視化を表示するには：
1. `visualization_url` にアクセス（Railway環境）
2. または `/visualization/{visualization_id}` エンドポイントにアクセス

---

## 🔍 トラブルシューティング

### 問題1: 404 Not Found

**原因**: キャッシュに保存されていない
**解決**: 可視化ツール内でユーザーキャッシュ保存処理が正しく実行されているか確認

### 問題2: undefined エラー

**原因**: パラメータ名が間違っている
**解決**: MCP_TOOLS_DEFINITIONの定義と一致させる

### 問題3: JSON parsing error

**原因**: JSON文字列パースが必要なのに実装されていない
**解決**: `json.loads()` 処理を追加

---

**テスト完了チェックリスト**:
- [ ] 1. visualize_last_optimization
- [ ] 2. visualize_inventory_simulation
- [ ] 3. visualize_demand_histogram
- [ ] 4. compare_inventory_costs_visual
- [ ] 5. visualize_forecast
- [ ] 6. visualize_periodic_optimization
- [ ] 7. visualize_safety_stock_network
- [ ] 8. visualize_eoq
- [ ] 9. visualize_simulation_trajectories
- [ ] 10. visualize_supply_chain_network

---

**作成者**: Claude Code
**バージョン**: 1.0
**最終更新**: 2025-10-11
