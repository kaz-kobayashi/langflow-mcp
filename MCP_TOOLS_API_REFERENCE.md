# MCP Tools API Reference

このドキュメントは、langflow-mcpプロジェクトで公開されている全34個のMCPツールのAPI仕様を記載しています。

**最終更新日**: 2025-10-09
**バージョン**: Phase 13完了時点

---

## 目次

### 在庫最適化
1. [optimize_safety_stock_allocation](#1-optimize_safety_stock_allocation) - 安全在庫配置の最適化（タブーサーチ）
2. [calculate_safety_stock](#2-calculate_safety_stock) - 安全在庫の計算
3. [calculate_base_stock_levels](#3-calculate_base_stock_levels) - 基在庫レベルの計算
4. [dynamic_programming_for_SSA](#4-dynamic_programming_for_ssa) - 動的計画法による安全在庫配置（厳密解）

### シミュレーション
5. [simulate_qr_policy](#5-simulate_qr_policy) - (Q,R)発注方策のシミュレーション
6. [simulate_ss_policy](#6-simulate_ss_policy) - (s,S)発注方策のシミュレーション
7. [simulate_base_stock_policy](#7-simulate_base_stock_policy) - 基在庫方策のシミュレーション
8. [simulate_multistage_inventory](#8-simulate_multistage_inventory) - 多段階在庫シミュレーション
9. [simulate_network_base_stock](#9-simulate_network_base_stock) - ネットワークベースストックシミュレーション
10. [base_stock_simulation_using_dist](#10-base_stock_simulation_using_dist) - 分布ベースの基在庫シミュレーション

### 発注方策の最適化
11. [optimize_qr_policy](#11-optimize_qr_policy) - (Q,R)発注方策の最適化
12. [optimize_ss_policy](#12-optimize_ss_policy) - (s,S)発注方策の最適化
13. [optimize_periodic_inventory](#13-optimize_periodic_inventory) - 定期発注方策の最適化
14. [optimize_periodic_with_one_cycle](#14-optimize_periodic_with_one_cycle) - ワンサイクルLR法による定期発注最適化

### 需要予測と分析
15. [forecast_demand](#15-forecast_demand) - 需要予測（指数平滑法、移動平均）
16. [analyze_demand_pattern](#16-analyze_demand_pattern) - 需要パターンの分析
17. [find_best_distribution](#17-find_best_distribution) - 最適な確率分布のフィッティング
18. [fit_histogram_distribution](#18-fit_histogram_distribution) - ヒストグラム分布のフィッティング

### EOQ（経済発注量）
19. [calculate_eoq_incremental_discount](#19-calculate_eoq_incremental_discount) - 増分数量割引EOQ
20. [calculate_eoq_all_units_discount](#20-calculate_eoq_all_units_discount) - 全単位数量割引EOQ

### Wagner-Whitinアルゴリズム
21. [calculate_wagner_whitin](#21-calculate_wagner_whitin) - Wagner-Whitin動的計画法

### 学習率最適化
22. [find_optimal_learning_rate_periodic](#22-find_optimal_learning_rate_periodic) - 定期発注の最適学習率探索（LR Finder）

### ネットワーク分析
23. [analyze_inventory_network](#23-analyze_inventory_network) - 在庫ネットワークの分析

### ポリシー比較
24. [compare_inventory_policies](#24-compare_inventory_policies) - 在庫方策の比較

### 可視化
25. [visualize_last_optimization](#25-visualize_last_optimization) - 最適化結果の可視化
26. [visualize_inventory_simulation](#26-visualize_inventory_simulation) - 在庫シミュレーション結果の可視化
27. [visualize_demand_histogram](#27-visualize_demand_histogram) - 需要ヒストグラムの可視化
28. [compare_inventory_costs_visual](#28-compare_inventory_costs_visual) - 在庫コストの視覚的比較
29. [visualize_forecast](#29-visualize_forecast) - 需要予測結果の可視化
30. [visualize_periodic_optimization](#30-visualize_periodic_optimization) - 定期発注最適化の可視化
31. [visualize_safety_stock_network](#31-visualize_safety_stock_network) - 安全在庫配置ネットワークの可視化
32. [visualize_eoq](#32-visualize_eoq) - EOQ分析の可視化
33. [visualize_supply_chain_network](#33-visualize_supply_chain_network) - サプライチェーンネットワークの可視化
34. [visualize_simulation_trajectories](#34-visualize_simulation_trajectories) - シミュレーション軌道の可視化

### ユーティリティ
35. [generate_sample_data](#35-generate_sample_data) - サンプルデータの生成

---

## 在庫最適化

### 1. optimize_safety_stock_allocation

**説明**: タブーサーチアルゴリズムを使用して、サプライチェーンネットワークの安全在庫配置を最適化します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
  - `name` (str): 品目名
  - `h` (float): 在庫保管費用
  - `b` (float): バックオーダーコスト
  - `average_demand` (float): 平均需要
  - `std_demand` (float): 需要の標準偏差
  - `lead_time` (float): リードタイム
  - `echelon_lead_time` (float): エシェロンリードタイム
- `bom_data` (list of dict, required): BOMデータ
  - `child` (str): 子品目名
  - `parent` (str): 親品目名
  - `units` (float): 使用単位数
- `z` (float, optional): サービスレベルのz値（デフォルト: 1.65）
- `max_iter` (int, optional): 最大反復回数（デフォルト: 100）
- `tabu_tenure` (int, optional): タブー期間（デフォルト: 5）

**出力**:
```json
{
  "status": "success",
  "best_cost": 123.45,
  "best_solution": {"item1": 10.5, "item2": 15.2},
  "iterations": 50,
  "cost_history": [150.0, 145.2, ...],
  "message": "..."
}
```

---

### 2. calculate_safety_stock

**説明**: 正規分布需要を仮定した安全在庫レベルを計算します。

**入力パラメータ**:
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (float, required): リードタイム
- `service_level` (float, optional): サービスレベル（デフォルト: 0.95）

**出力**:
```json
{
  "status": "success",
  "safety_stock": 45.67,
  "z_value": 1.65,
  "service_level": 0.95,
  "lead_time_demand_std": 27.39,
  "message": "..."
}
```

---

### 3. calculate_base_stock_levels

**説明**: サプライチェーンネットワークの各段階の基在庫レベルを計算します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
- `bom_data` (list of dict, required): BOMデータ
- `z` (float, optional): サービスレベルのz値（デフォルト: 1.65）

**出力**:
```json
{
  "status": "success",
  "base_stock_levels": {"item1": 250.5, "item2": 180.3},
  "echelon_lead_times": {"item1": 5.0, "item2": 3.0},
  "message": "..."
}
```

---

### 4. dynamic_programming_for_SSA

**説明**: 動的計画法を使用して、ツリー構造のサプライチェーンネットワークに対する安全在庫配置の厳密解を求めます（Graves & Willems, 2003）。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
  - `name` (str): 品目名
  - `h` (float): 在庫保管費用
  - `mu` (float): 平均需要（最終製品のみ）
  - `sigma` (float): 需要の標準偏差（最終製品のみ）
  - `proc_time` (int): 処理時間
  - `lead_time_lb` (int): リードタイム下限
  - `lead_time_ub` (int): リードタイム上限
- `bom_data` (list of dict, required): BOMデータ
- `z` (float, optional): サービスレベルのz値（デフォルト: 1.65）

**出力**:
```json
{
  "status": "success",
  "total_cost": 165.0,
  "guaranteed_lead_times": {"item1": 2.0, "item2": 1.0},
  "net_replenishment_times": {"item1": 0.0, "item2": 3.0},
  "safety_stock_levels": {"item1": 0.0, "item2": 33.0},
  "optimization_params": {
    "z_value": 1.65,
    "service_level": "95.1%",
    "n_items": 3,
    "network_type": "tree"
  },
  "message": "..."
}
```

**制約**:
- ネットワークはツリー構造でなければならない
- サイクルは許可されない

---

## シミュレーション

### 5. simulate_qr_policy

**説明**: (Q,R)連続発注方策のシミュレーションを実行します。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `Q` (float, required): 発注量
- `R` (float, required): 発注点
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (int, required): リードタイム
- `holding_cost` (float, optional): 在庫保管費用（デフォルト: 1）
- `backorder_cost` (float, optional): バックオーダーコスト（デフォルト: 100）
- `fixed_cost` (float, optional): 固定発注コスト（デフォルト: 100）

**出力**:
```json
{
  "status": "success",
  "average_cost": 234.56,
  "average_inventory": 45.23,
  "service_level": 0.95,
  "stockout_rate": 0.05,
  "message": "..."
}
```

---

### 6. simulate_ss_policy

**説明**: (s,S)連続発注方策のシミュレーションを実行します。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `s` (float, required): 発注点
- `S` (float, required): 最大在庫レベル
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (int, required): リードタイム
- `holding_cost` (float, optional): 在庫保管費用
- `backorder_cost` (float, optional): バックオーダーコスト
- `fixed_cost` (float, optional): 固定発注コスト

**出力**:
```json
{
  "status": "success",
  "average_cost": 245.67,
  "average_inventory": 50.12,
  "service_level": 0.96,
  "message": "..."
}
```

---

### 7. simulate_base_stock_policy

**説明**: 基在庫方策（定期発注方策）のシミュレーションを実行します。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `base_stock_level` (float, required): 基在庫レベル
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (int, required): リードタイム
- `holding_cost` (float, optional): 在庫保管費用
- `backorder_cost` (float, optional): バックオーダーコスト

**出力**:
```json
{
  "status": "success",
  "average_cost": 198.45,
  "inventory_stats": {
    "mean": 45.2,
    "std": 12.3,
    "min": 10.5,
    "max": 80.1
  },
  "message": "..."
}
```

---

### 8. simulate_multistage_inventory

**説明**: 多段階在庫システムのシミュレーションを実行します。結果は自動的にキャッシュされ、後で可視化に使用できます。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `n_stages` (int, required): 段階数
- `mu` (float, required): 需要の平均
- `sigma` (float, optional): 需要の標準偏差（デフォルト: mu/10）
- `LT` (list of int, optional): 各段階のリードタイム
- `s` (list of float, optional): 各段階の発注点
- `S` (list of float, optional): 各段階の基在庫レベル
- `h` (list of float, optional): 各段階の在庫保管費用
- `b` (float, optional): バックオーダーコスト
- `fc` (float, optional): 固定発注コスト

**出力**:
```json
{
  "status": "success",
  "average_cost": 456.78,
  "simulation_params": {...},
  "inventory_stats": [...],
  "message": "シミュレーションを実行しました。結果は保存されました（後で可視化できます）。"
}
```

---

### 9. simulate_network_base_stock

**説明**: 複雑なネットワーク構造（線形、分岐、合流）を持つサプライチェーンで基在庫シミュレーションを実行します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
  - `name` (str): 品目名
  - `h` (float): 在庫保管費用
  - `b` (float): バックオーダーコスト
  - `average_demand` (float): 平均需要
  - `std_demand` (float): 需要の標準偏差
  - `lead_time` (int): リードタイム
  - `echelon_lead_time` (int): エシェロンリードタイム
  - `capacity` (float, optional): 生産能力
- `bom_data` (list of dict, required): BOMデータ
  - `allocation` (float, optional): 配分率
- `n_samples` (int, optional): サンプル数
- `n_periods` (int, optional): シミュレーション期間
- `base_stock_levels` (dict, optional): 基在庫レベル

**出力**:
```json
{
  "status": "success",
  "total_cost": 567.89,
  "gradient": [1.2, 0.8, ...],
  "inventory_stats": [...],
  "message": "..."
}
```

---

### 10. base_stock_simulation_using_dist

**説明**: 確率分布オブジェクトから需要を生成して、単一段階基在庫シミュレーションを実行します。

**入力パラメータ**:
- `n_samples` (int, optional): サンプル数（デフォルト: 100）
- `n_periods` (int, optional): シミュレーション期間（デフォルト: 100）
- `demand_dist` (dict, required): 需要分布の設定
  - `type` (str): 分布のタイプ（"normal", "uniform", "exponential", "poisson", "gamma", "lognormal"）
  - `params` (dict): 分布のパラメータ
- `capacity` (float, optional): 生産能力（デフォルト: 無限大）
- `lead_time` (int, optional): リードタイム（デフォルト: 1）
- `backorder_cost` (float, optional): バックオーダーコスト（デフォルト: 100）
- `holding_cost` (float, optional): 在庫保管費用（デフォルト: 1）
- `base_stock_level` (float, optional): 基在庫レベル（未指定時は自動計算）

**分布パラメータの例**:
```json
// 正規分布
{"type": "normal", "params": {"mu": 100, "sigma": 10}}

// 一様分布
{"type": "uniform", "params": {"low": 80, "high": 120}}

// ポアソン分布
{"type": "poisson", "params": {"lam": 100}}

// ガンマ分布
{"type": "gamma", "params": {"shape": 2, "scale": 50}}

// 対数正規分布
{"type": "lognormal", "params": {"s": 0.5, "scale": 100}}

// 指数分布
{"type": "exponential", "params": {"scale": 100}}
```

**出力**:
```json
{
  "status": "success",
  "gradient": 1.0,
  "average_cost": 173.99,
  "base_stock_level": 369.9,
  "inventory_stats": {
    "mean_inventory": 172.27,
    "std_inventory": 26.15,
    "min_inventory": 117.97,
    "max_inventory": 369.9,
    "stockout_rate": 0.0,
    "avg_backorder": 0.0
  },
  "simulation_params": {...},
  "message": "..."
}
```

---

## 発注方策の最適化

### 11. optimize_qr_policy

**説明**: (Q,R)連続発注方策のパラメータを最適化します。

**入力パラメータ**:
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (int, required): リードタイム
- `holding_cost` (float, optional): 在庫保管費用
- `backorder_cost` (float, optional): バックオーダーコスト
- `fixed_cost` (float, optional): 固定発注コスト
- `n_samples` (int, optional): シミュレーションサンプル数
- `n_periods` (int, optional): シミュレーション期間

**出力**:
```json
{
  "status": "success",
  "optimal_Q": 150.5,
  "optimal_R": 80.3,
  "expected_cost": 234.56,
  "message": "..."
}
```

---

### 12. optimize_ss_policy

**説明**: (s,S)連続発注方策のパラメータを最適化します。

**入力パラメータ**:
- 同上（`optimize_qr_policy`と同様）

**出力**:
```json
{
  "status": "success",
  "optimal_s": 75.2,
  "optimal_S": 200.8,
  "expected_cost": 245.67,
  "message": "..."
}
```

---

### 13. optimize_periodic_inventory

**説明**: 定期発注方策の基在庫レベルを最適化します（Adam、SGD、Momentum対応）。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `n_stages` (int, required): 段階数
- `mu` (float, required): 需要の平均
- `sigma` (float, optional): 需要の標準偏差
- `LT` (list of int, optional): リードタイム
- `h` (list of float, optional): 在庫保管費用
- `b` (float, optional): バックオーダーコスト
- `fc` (float, optional): 固定発注コスト
- `learning_rate` (float, optional): 学習率（デフォルト: 0.1）
- `max_iterations` (int, optional): 最大反復回数（デフォルト: 100）
- `convergence_threshold` (float, optional): 収束判定閾値（デフォルト: 0.1）
- `optimizer` (str, optional): 最適化アルゴリズム（"sgd", "momentum", "adam"、デフォルト: "adam"）
- `momentum` (float, optional): Momentum係数（デフォルト: 0.9）
- `beta1` (float, optional): Adam β1（デフォルト: 0.9）
- `beta2` (float, optional): Adam β2（デフォルト: 0.999）

**出力**:
```json
{
  "status": "success",
  "optimal_base_stock_levels": [250.5, 180.3, 150.2],
  "final_cost": 345.67,
  "iterations": 45,
  "cost_history": [...],
  "convergence_info": {...},
  "message": "..."
}
```

---

### 14. optimize_periodic_with_one_cycle

**説明**: ワンサイクルLR法を使用して定期発注方策を最適化します。

**入力パラメータ**:
- 基本パラメータは`optimize_periodic_inventory`と同様
- `lr_max` (float, optional): 最大学習率（デフォルト: 1.0）
- `lr_min` (float, optional): 最小学習率（デフォルト: 0.001）
- `cycle_momentum_min` (float, optional): 最小Momentum（デフォルト: 0.85）
- `cycle_momentum_max` (float, optional): 最大Momentum（デフォルト: 0.95）

**出力**:
```json
{
  "status": "success",
  "optimal_base_stock_levels": [...],
  "final_cost": 345.67,
  "learning_rate_schedule": [...],
  "momentum_schedule": [...],
  "message": "..."
}
```

---

## 需要予測と分析

### 15. forecast_demand

**説明**: 需要予測を実行します（指数平滑法、移動平均法）。

**入力パラメータ**:
- `historical_demand` (list of float, required): 過去の需要データ
- `forecast_periods` (int, required): 予測期間
- `method` (str, optional): 予測手法（"ses", "des", "ma"、デフォルト: "ses"）
- `alpha` (float, optional): 平滑化係数（デフォルト: 0.3）
- `beta` (float, optional): トレンド平滑化係数（デフォルト: 0.1）
- `window` (int, optional): 移動平均の窓サイズ（デフォルト: 3）

**出力**:
```json
{
  "status": "success",
  "forecast": [120.5, 125.3, ...],
  "method": "ses",
  "parameters": {"alpha": 0.3},
  "message": "..."
}
```

---

### 16. analyze_demand_pattern

**説明**: 需要パターンを分析します（トレンド、季節性、統計量）。

**入力パラメータ**:
- `demand_data` (list of float, required): 需要データ

**出力**:
```json
{
  "status": "success",
  "statistics": {
    "mean": 105.3,
    "std": 12.5,
    "cv": 0.119,
    "min": 80.0,
    "max": 150.0
  },
  "trend_analysis": {
    "has_trend": true,
    "trend_slope": 2.3,
    "trend_direction": "increasing"
  },
  "seasonality_info": {...},
  "message": "..."
}
```

---

### 17. find_best_distribution

**説明**: 需要データに最適な確率分布をフィッティングします。

**入力パラメータ**:
- `demand_data` (list of float, required): 需要データ
- `distributions` (list of str, optional): 試行する分布のリスト

**出力**:
```json
{
  "status": "success",
  "best_distribution": "gamma",
  "best_params": {"a": 12.5, "loc": 0, "scale": 8.3},
  "aic": 456.78,
  "bic": 467.89,
  "all_results": [...],
  "message": "..."
}
```

---

### 18. fit_histogram_distribution

**説明**: ヒストグラム形式の確率分布を作成します。

**入力パラメータ**:
- `demand_data` (list of float, required): 需要データ
- `nbins` (int, optional): ビン数（デフォルト: 50）

**出力**:
```json
{
  "status": "success",
  "distribution_type": "histogram",
  "n_bins": 50,
  "histogram_data": {
    "counts": [...],
    "bin_edges": [...]
  },
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

## EOQ（経済発注量）

### 19. calculate_eoq_incremental_discount

**説明**: 増分数量割引を考慮したEOQを計算します。

**入力パラメータ**:
- `demand_rate` (float, required): 年間需要率
- `ordering_cost` (float, required): 発注コスト
- `holding_cost_rate` (float, required): 在庫保管費率
- `unit_prices` (list of dict, required): 価格ブレークポイント
  - `quantity` (float): 数量
  - `price` (float): 単価

**出力**:
```json
{
  "status": "success",
  "optimal_order_quantity": 500.0,
  "total_cost": 12345.67,
  "unit_price": 10.5,
  "number_of_orders": 24,
  "message": "..."
}
```

---

### 20. calculate_eoq_all_units_discount

**説明**: 全単位数量割引を考慮したEOQを計算します。

**入力パラメータ**:
- 同上（`calculate_eoq_incremental_discount`と同様）

**出力**:
```json
{
  "status": "success",
  "optimal_order_quantity": 800.0,
  "total_cost": 11234.56,
  "unit_price": 9.8,
  "message": "..."
}
```

---

## Wagner-Whitinアルゴリズム

### 21. calculate_wagner_whitin

**説明**: Wagner-Whitin動的計画法アルゴリズムを使用して、時間変動需要に対する最適発注計画を計算します。

**入力パラメータ**:
- `demand` (list of float, required): 各期の需要
- `ordering_cost` (float, required): 固定発注コスト
- `holding_cost` (float, required): 単位在庫保管費用

**出力**:
```json
{
  "status": "success",
  "total_cost": 567.89,
  "order_schedule": [0, 150, 0, 200, ...],
  "inventory_levels": [0, 100, 50, ...],
  "message": "..."
}
```

---

## 学習率最適化

### 22. find_optimal_learning_rate_periodic

**説明**: LR Finder法を使用して、定期発注最適化の最適学習率を探索します。

**入力パラメータ**:
- `n_samples` (int, required): サンプル数
- `n_periods` (int, required): シミュレーション期間
- `n_stages` (int, required): 段階数
- `mu` (float, required): 需要の平均
- `sigma` (float, optional): 需要の標準偏差
- `lr_min` (float, optional): 最小学習率（デフォルト: 0.001）
- `lr_max` (float, optional): 最大学習率（デフォルト: 10.0）
- `num_iterations` (int, optional): 探索反復回数（デフォルト: 100）
- `smoothing` (float, optional): 平滑化係数（デフォルト: 0.05）

**出力**:
```json
{
  "status": "success",
  "suggested_lr": 0.15,
  "lr_history": [...],
  "cost_history": [...],
  "smoothed_cost_history": [...],
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

## ネットワーク分析

### 23. analyze_inventory_network

**説明**: サプライチェーンネットワークの構造を分析します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
- `bom_data` (list of dict, required): BOMデータ

**出力**:
```json
{
  "status": "success",
  "network_info": {
    "num_nodes": 5,
    "num_edges": 4,
    "is_dag": true,
    "is_tree": true,
    "has_cycles": false,
    "num_levels": 3
  },
  "node_analysis": [...],
  "message": "..."
}
```

---

## ポリシー比較

### 24. compare_inventory_policies

**説明**: 複数の在庫方策を比較します。

**入力パラメータ**:
- `demand_mean` (float, required): 需要の平均
- `demand_std` (float, required): 需要の標準偏差
- `lead_time` (int, required): リードタイム
- `holding_cost` (float, optional): 在庫保管費用
- `backorder_cost` (float, optional): バックオーダーコスト
- `fixed_cost` (float, optional): 固定発注コスト
- `n_samples` (int, optional): サンプル数
- `n_periods` (int, optional): シミュレーション期間

**出力**:
```json
{
  "status": "success",
  "comparison_results": {
    "qr_policy": {...},
    "ss_policy": {...},
    "base_stock_policy": {...}
  },
  "best_policy": "base_stock_policy",
  "message": "..."
}
```

---

## 可視化

### 25. visualize_last_optimization

**説明**: 最後に実行した最適化の結果を可視化します。

**入力パラメータ**:
- なし（最後の最適化結果を自動取得）

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "visualization_type": "最適化結果",
  "message": "..."
}
```

---

### 26. visualize_inventory_simulation

**説明**: 在庫シミュレーション結果を可視化します。

**入力パラメータ**:
- `simulation_results` (dict, required): シミュレーション結果

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

### 27. visualize_demand_histogram

**説明**: 需要データのヒストグラムと確率密度を可視化します。

**入力パラメータ**:
- `demand_data` (list of float, required): 需要データ
- `nbins` (int, optional): ビン数（デフォルト: 50）
- `show_distribution` (bool, optional): フィッティング分布を表示（デフォルト: true）

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "distribution_info": {...},
  "message": "..."
}
```

---

### 28. compare_inventory_costs_visual

**説明**: 異なる在庫方策のコストを視覚的に比較します。

**入力パラメータ**:
- `comparison_results` (dict, required): 比較結果

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

### 29. visualize_forecast

**説明**: 需要予測結果を可視化します。

**入力パラメータ**:
- `historical_demand` (list of float, required): 過去の需要データ
- `forecast` (list of float, required): 予測値
- `method` (str, optional): 予測手法名

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

### 30. visualize_periodic_optimization

**説明**: 定期発注最適化の収束過程を可視化します。

**入力パラメータ**:
- `cost_history` (list of float, required): コスト履歴
- `base_stock_history` (list of list, optional): 基在庫レベル履歴

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

### 31. visualize_safety_stock_network

**説明**: 安全在庫配置ネットワークを可視化します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
- `bom_data` (list of dict, required): BOMデータ
- `safety_stock_levels` (dict, optional): 安全在庫レベル

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "message": "..."
}
```

---

### 32. visualize_eoq

**説明**: EOQ分析の総コスト曲線を可視化します。

**入力パラメータ**:
- `demand_rate` (float, required): 年間需要率
- `ordering_cost` (float, required): 発注コスト
- `holding_cost_rate` (float, required): 在庫保管費率
- `unit_price` (float, required): 単価
- `eoq` (float, optional): EOQ値（未指定時は自動計算）

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "eoq": 500.0,
  "message": "..."
}
```

---

### 33. visualize_supply_chain_network

**説明**: サプライチェーンネットワーク構造を可視化します。

**入力パラメータ**:
- `items_data` (list of dict, required): 品目データ
- `bom_data` (list of dict, required): BOMデータ
- `layout` (str, optional): レイアウト（"hierarchical", "spring"、デフォルト: "hierarchical"）

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "network_stats": {...},
  "message": "..."
}
```

---

### 34. visualize_simulation_trajectories

**説明**: 多段階在庫シミュレーションの軌道を可視化します。キャッシュから自動的にデータを取得できます。

**入力パラメータ**:
- `inventory_data` (array, optional): 在庫データ（未指定時はキャッシュから取得）
- `n_periods` (int, optional): 期間数
- `samples` (int, optional): 表示サンプル数（デフォルト: 5）
- `stage_names` (list of str, optional): 段階名
- `stage_id_list` (list of int, optional): 表示する段階ID

**出力**:
```json
{
  "status": "success",
  "visualization_id": "uuid-string",
  "visualization_type": "シミュレーション軌道",
  "statistics": [...],
  "params": {...},
  "message": "..."
}
```

**自然な使用フロー**:
1. `simulate_multistage_inventory`を実行（結果は自動保存）
2. 「可視化してください」と指示するだけで自動的にキャッシュから取得して可視化

---

## ユーティリティ

### 35. generate_sample_data

**説明**: テスト用のサンプルデータを生成します。

**入力パラメータ**:
- `data_type` (str, required): データタイプ（"demand", "items", "bom"）
- `n_items` (int, optional): 品目数
- `n_periods` (int, optional): 期間数

**出力**:
```json
{
  "status": "success",
  "data": [...],
  "data_type": "demand",
  "message": "..."
}
```

---

## エラーハンドリング

全てのMCPツールは以下の形式でエラーを返します：

```json
{
  "status": "error",
  "message": "エラーメッセージ",
  "traceback": "詳細なトレースバック（デバッグ用）"
}
```

---

## 使用上の注意

### パフォーマンス

- **シミュレーション**: サンプル数や期間が大きい場合、計算時間が増加します
  - 推奨: `n_samples` ≤ 200, `n_periods` ≤ 300

- **最適化**: 反復回数が多い場合、計算時間が増加します
  - 推奨: `max_iterations` ≤ 200

- **ネットワーク**: ノード数が多い場合、計算時間が増加します
  - 推奨: ノード数 ≤ 50

### キャッシュ機構

以下のツールは結果を自動的にキャッシュします：
- `simulate_multistage_inventory`
- `optimize_safety_stock_allocation`
- `optimize_periodic_inventory`
- `find_optimal_learning_rate_periodic`

キャッシュされた結果は、対応する可視化ツールで自動的に使用されます。

---

## バージョン履歴

- **Phase 13 (2025-10-09)**:
  - `dynamic_programming_for_SSA`追加
  - `base_stock_simulation_using_dist`追加
- **Phase 12 (2025-10-08)**:
  - `simulate_network_base_stock`追加
  - `visualize_simulation_trajectories`追加
  - キャッシュ機構実装
- **Phase 11**: ネットワーク可視化、ヒストグラムフィット、多段階シミュレーション
- **Phase 10**: LR Finder、ワンサイクルLR法
- **Phase 9**: EOQ計算
- **Phase 8**: 安全在庫ネットワーク可視化
- **Phase 7**: 定期発注最適化（Adam対応）
- **Phase 6**: 需要予測

---

## 関連ドキュメント

- `PHASE13_INPUT_EXAMPLES.md`: Phase 13の動作確認用入力例
- `PHASE13_SUMMARY.md`: Phase 13実装サマリー
- `IMPLEMENTATION_SUMMARY.md`: Phase 12実装サマリー
- `LOCAL_DEVELOPMENT.md`: ローカル開発環境のセットアップガイド
