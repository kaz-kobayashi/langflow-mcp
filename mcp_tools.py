"""
MCP Tools integration for OpenAI Function Calling
"""

import json
import sys
sys.path.append('.')

from scmopt2.optinv import (
    eoq,
    approximate_ss,
    tabu_search_for_SSA,
    make_excel_messa,
    prepare_opt_for_messa,
    draw_graph_for_SSA,
    simulate_inventory,
    optimize_qr,
    optimize_ss,
    ww,
    best_distribution,
    best_histogram
)
from fixed_multistage import (
    multi_stage_simulate_inventory_fixed,
    base_stock_simulation_fixed,
    multi_stage_base_stock_simulation_fixed,
    initial_base_stock_level_fixed
)
from forecast_utils import forecast_demand as forecast_demand_util
from periodic_optimizer import optimize_periodic_inventory as optimize_periodic_util, prepare_stage_bom_data
from network_visualizer import visualize_safety_stock_network, prepare_network_visualization_data
from eoq_calculator import (
    calculate_eoq as calc_eoq_basic,
    calculate_eoq_with_incremental_discount,
    calculate_eoq_with_all_units_discount,
    visualize_eoq_analysis,
    visualize_eoq_with_discount
)
from lr_finder import (
    find_optimal_learning_rate,
    optimize_with_one_cycle,
    visualize_lr_search,
    visualize_training_progress
)
import numpy as np
import plotly.io as pio
import plotly.graph_objects as go
from scipy import stats
import os
import uuid
from datetime import datetime

# ユーザーごとの計算結果キャッシュ
# {user_id: {"G": graph, "pos": positions, "best_sol": solution, "items": items_data, "bom": bom_data}}
_optimization_cache = {}


def get_visualization_html(user_id: int, viz_id: str = None) -> str:
    """ユーザーの可視化HTMLを取得"""
    if user_id not in _optimization_cache:
        raise KeyError(f"No cache found for user_id: {user_id}")

    cache = _optimization_cache[user_id]

    # viz_idが指定されている場合は、そのIDの可視化を返す
    if viz_id:
        if viz_id not in cache:
            raise KeyError(f"No visualization found for viz_id: {viz_id}")
        return cache[viz_id]

    # 後方互換性: viz_idが指定されていない場合は古い動作
    if "visualization_html" not in cache:
        raise KeyError(f"No visualization_html found for user_id: {user_id}")

    return cache["visualization_html"]


# OpenAI Function Calling用のツール定義
MCP_TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "calculate_eoq",
            "description": "経済発注量（EOQ: Economic Order Quantity）を計算します。発注固定費用、平均需要量、在庫保管費用、品切れ費用から最適な発注量を算出します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "K": {
                        "type": "number",
                        "description": "発注固定費用（円/回）"
                    },
                    "d": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "h": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "b": {
                        "type": "number",
                        "description": "品切れ費用（円/unit/日）"
                    }
                },
                "required": ["K", "d", "h", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_safety_stock",
            "description": "安全在庫レベルを計算します。リードタイム、需要の平均と標準偏差、各種コストから最適な安全在庫量を算出します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "LT": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "b": {
                        "type": "number",
                        "description": "品切れ費用（円/unit/日）"
                    },
                    "h": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "fc": {
                        "type": "number",
                        "description": "発注固定費用（円/回）",
                        "default": 10000.0
                    }
                },
                "required": ["mu", "sigma", "LT", "b", "h"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_safety_stock_allocation",
            "description": "マルチエシュロン在庫ネットワーク全体での安全在庫配置を最適化します（MESSA: MEta Safety Stock Allocation）。品目データとBOM（部品表）から、各拠点の最適な安全在庫レベルを計算します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items_data": {
                        "type": "string",
                        "description": "品目データのJSON配列文字列。各品目には name, process_time, max_service_time, avg_demand, demand_std, holding_cost, stockout_cost, fixed_cost が含まれます。"
                    },
                    "bom_data": {
                        "type": "string",
                        "description": "BOM（部品表）データのJSON配列文字列。各エントリには child（子品目）, parent（親品目）, quantity（必要量）が含まれます。"
                    }
                },
                "required": ["items_data", "bom_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_inventory_network",
            "description": "在庫ネットワークの構造を分析し、ノード数、エッジ数、各拠点のコスト情報などを返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items_data": {
                        "type": "string",
                        "description": "品目データのJSON配列文字列"
                    },
                    "bom_data": {
                        "type": "string",
                        "description": "BOMデータのJSON配列文字列"
                    }
                },
                "required": ["items_data", "bom_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_last_optimization",
            "description": "直前に実行した安全在庫最適化(optimize_safety_stock_allocation)の結果を可視化します。ユーザーが「結果を可視化して」「グラフを見せて」「図を表示して」などと依頼した場合に使用します。データを再度指定する必要はありません。グラフや図、チャート、ネットワーク図が必要な時は、まずoptimize_safety_stock_allocationを実行してから、このツールを使用してください。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sample_data",
            "description": "サプライチェーンネットワーク最適化のためのサンプルデータを生成します。ユーザーがデータ形式がわからない場合や、例を見たい場合に使用します。シンプル（3品目）、標準（5品目）、複雑（8品目）の3パターンから選べます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "standard", "complex"],
                        "description": "サンプルデータの複雑さ。simple=3品目の直列ネットワーク、standard=5品目の分岐あり、complex=8品目の複雑なネットワーク"
                    }
                },
                "required": ["complexity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_qr_policy",
            "description": "(Q,R)方策の在庫シミュレーションを実行します。発注量Qと発注点Rを指定して、在庫コスト、サービスレベル、在庫推移などをシミュレーションします。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "Q": {
                        "type": "number",
                        "description": "発注量（units）"
                    },
                    "R": {
                        "type": "number",
                        "description": "発注点（units）- 在庫がこのレベルを下回ったら発注"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "Q", "R", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_qr_policy",
            "description": "(Q,R)方策の最適パラメータを計算します。シミュレーションベースの最適化により、最適な発注量Qと発注点Rを求めます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_ss_policy",
            "description": "(s,S)方策の在庫シミュレーションを実行します。発注点sと基在庫レベルSを指定して、在庫コスト、サービスレベル、在庫推移などをシミュレーションします。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "s": {
                        "type": "number",
                        "description": "発注点（units）- 在庫がこのレベルを下回ったら発注"
                    },
                    "S": {
                        "type": "number",
                        "description": "基在庫レベル（units）- 発注時にこのレベルまで補充"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "s", "S", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_ss_policy",
            "description": "(s,S)方策の最適パラメータを計算します。シミュレーションベースの最適化により、最適な発注点sと基在庫レベルSを求めます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_wagner_whitin",
            "description": "Wagner-Whitinアルゴリズムを使用して、動的ロットサイジング問題を解きます。将来の需要が既知の場合に、総コストを最小化する発注スケジュールを計算します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "各期の需要量の配列（例: [10, 20, 30, 15]）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/期）"
                    },
                    "variable_cost": {
                        "type": "number",
                        "description": "変動発注費用（円/unit）（デフォルト: 0）"
                    }
                },
                "required": ["demand", "fixed_cost", "holding_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_demand_pattern",
            "description": "需要データの統計的分析を行い、平均、標準偏差、変動係数などを計算します。需要パターンの理解と在庫方策の選択に役立ちます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "需要データの配列（例: [10, 12, 8, 15, 11]）"
                    }
                },
                "required": ["demand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_inventory_policies",
            "description": "EOQ、(Q,R)方策、(s,S)方策の3つの在庫方策を同じ条件で比較し、最もコスト効率の良い方策を推奨します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_safety_stock",
            "description": "目標サービスレベルに基づいて必要な安全在庫を計算します。正規分布を仮定し、リードタイム需要の変動を考慮します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "service_level": {
                        "type": "number",
                        "description": "目標サービスレベル（0-1の範囲、例: 0.95 = 95%）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）（オプション）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "service_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_inventory_simulation",
            "description": "在庫方策のシミュレーション結果を可視化します。在庫レベルの推移、発注タイミング、品切れ状況をグラフで表示します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "policy_type": {
                        "type": "string",
                        "enum": ["QR", "sS"],
                        "description": "在庫方策のタイプ: 'QR' = (Q,R)方策、'sS' = (s,S)方策"
                    },
                    "Q": {
                        "type": "number",
                        "description": "(Q,R)方策の場合の発注量（policy_type='QR'の場合必須）"
                    },
                    "R": {
                        "type": "number",
                        "description": "(Q,R)方策の場合の発注点（policy_type='QR'の場合必須）"
                    },
                    "s": {
                        "type": "number",
                        "description": "(s,S)方策の場合の発注点（policy_type='sS'の場合必須）"
                    },
                    "S": {
                        "type": "number",
                        "description": "(s,S)方策の場合の基在庫レベル（policy_type='sS'の場合必須）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "policy_type", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_best_distribution",
            "description": "需要データに最適な確率分布を自動的に見つけてフィッティングします。正規分布、ガンマ分布、対数正規分布など複数の分布を試し、最も適合度の高いものを選択します。フィッティング結果を可視化します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "需要データの配列（例: [10, 12, 8, 15, 11, 9, 13, 10, 14, 11]）"
                    }
                },
                "required": ["demand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_demand_histogram",
            "description": "需要データのヒストグラムを作成し、基本統計量とともに可視化します。需要の分布パターンを視覚的に理解するのに役立ちます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "需要データの配列（例: [10, 12, 8, 15, 11]）"
                    },
                    "nbins": {
                        "type": "integer",
                        "description": "ヒストグラムのビン数（デフォルト: 30）"
                    }
                },
                "required": ["demand"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_inventory_costs_visual",
            "description": "複数の在庫方策のコストを棒グラフで比較可視化します。EOQ、(Q,R)、(s,S)の3つの方策のコストを並べて表示し、最適方策の選択を支援します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mu": {
                        "type": "number",
                        "description": "1日あたりの平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "fixed_cost": {
                        "type": "number",
                        "description": "固定発注費用（円/回）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（日）（デフォルト：100）"
                    }
                },
                "required": ["mu", "sigma", "lead_time", "holding_cost", "stockout_cost", "fixed_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_base_stock_policy",
            "description": "ベースストック方策（定期発注方策）のシミュレーションを実行します。毎期、在庫ポジションをベースストックレベルSまで補充する方策の性能を評価します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "需要データの配列。例: [10.5, 12.3, 8.7, ...]"
                    },
                    "base_stock_level": {
                        "type": "number",
                        "description": "ベースストックレベルS（目標在庫水準）"
                    },
                    "lead_time": {
                        "type": "integer",
                        "description": "リードタイム（日）"
                    },
                    "capacity": {
                        "type": "number",
                        "description": "生産能力上限（units/日）"
                    },
                    "holding_cost": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "stockout_cost": {
                        "type": "number",
                        "description": "品切れ費用（円/unit）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：5）"
                    }
                },
                "required": ["demand", "base_stock_level", "lead_time", "capacity", "holding_cost", "stockout_cost"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_base_stock_levels",
            "description": "サプライチェーンネットワークの各ノードにおける初期ベースストックレベルを計算します。リードタイム、需要特性、サービス水準から最適な在庫水準を決定します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "lead_time": {"type": "integer"}
                            }
                        },
                        "description": "ノード情報の配列。各ノードは名前とリードタイムを持つ。例: [{\"name\": \"retailer\", \"lead_time\": 1}, {\"name\": \"warehouse\", \"lead_time\": 3}]"
                    },
                    "mu": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "sigma": {
                        "type": "number",
                        "description": "需要の標準偏差"
                    },
                    "service_level": {
                        "type": "number",
                        "description": "サービス水準（0-1の値、例: 0.95で95%）"
                    }
                },
                "required": ["nodes", "mu", "sigma", "service_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_demand",
            "description": "過去の需要データから未来の需要を予測します。移動平均法、指数平滑法、線形トレンド法の3つの手法をサポートし、予測区間も計算します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand_history": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "過去の需要データ配列。例: [10, 12, 8, 15, 11, 9, 13]"
                    },
                    "forecast_periods": {
                        "type": "integer",
                        "description": "予測する期間数（デフォルト：7）"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["moving_average", "exponential_smoothing", "linear_trend"],
                        "description": "予測手法。moving_average（移動平均法）、exponential_smoothing（指数平滑法）、linear_trend（線形トレンド法）から選択"
                    },
                    "confidence_level": {
                        "type": "number",
                        "description": "信頼水準（0-1の値、例: 0.95で95%信頼区間）。デフォルト：0.95"
                    },
                    "window": {
                        "type": "integer",
                        "description": "移動平均法の窓サイズ（moving_averageの場合のみ使用）"
                    },
                    "alpha": {
                        "type": "number",
                        "description": "指数平滑法の平滑化パラメータ（0-1、exponential_smoothingの場合のみ使用）。デフォルト：0.3"
                    }
                },
                "required": ["demand_history"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_forecast",
            "description": "需要予測結果を時系列グラフとして可視化します。過去データ、予測値、信頼区間を1つのグラフで表示します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "demand_history": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "過去の需要データ配列"
                    },
                    "forecast_periods": {
                        "type": "integer",
                        "description": "予測する期間数（デフォルト：7）"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["moving_average", "exponential_smoothing", "linear_trend"],
                        "description": "予測手法"
                    },
                    "confidence_level": {
                        "type": "number",
                        "description": "信頼水準（デフォルト：0.95）"
                    }
                },
                "required": ["demand_history"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_periodic_inventory",
            "description": "定期発注方策の最適化（Adam最適化アルゴリズムによる基在庫レベル最適化）。サプライチェーンネットワークの各ステージの基在庫レベルを最適化し、総コストを最小化します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "network_data": {
                        "type": "object",
                        "description": "ネットワーク定義（stagesとconnectionsを含む）",
                        "properties": {
                            "stages": {
                                "type": "array",
                                "description": "ステージ情報のリスト",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "ステージ名"},
                                        "average_demand": {"type": "number", "description": "平均需要"},
                                        "sigma": {"type": "number", "description": "需要の標準偏差"},
                                        "h": {"type": "number", "description": "在庫保管コスト"},
                                        "b": {"type": "number", "description": "欠品コスト"},
                                        "z": {"type": "number", "description": "安全係数（オプション：未指定時は自動計算）"},
                                        "capacity": {"type": "number", "description": "生産能力"},
                                        "net_replenishment_time": {"type": "number", "description": "正味補充時間"},
                                        "x": {"type": "number", "description": "X座標（オプション：可視化用）"},
                                        "y": {"type": "number", "description": "Y座標（オプション：可視化用）"}
                                    },
                                    "required": ["name", "average_demand", "sigma", "h", "b", "capacity", "net_replenishment_time"]
                                }
                            },
                            "connections": {
                                "type": "array",
                                "description": "接続情報のリスト",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "child": {"type": "string", "description": "子ノード名"},
                                        "parent": {"type": "string", "description": "親ノード名"},
                                        "units": {"type": "number", "description": "使用単位数"},
                                        "allocation": {"type": "number", "description": "配分比率"}
                                    }
                                }
                            }
                        }
                    },
                    "max_iter": {
                        "type": "integer",
                        "description": "最大反復回数（デフォルト：100）"
                    },
                    "n_samples": {
                        "type": "integer",
                        "description": "シミュレーションサンプル数（デフォルト：10）"
                    },
                    "n_periods": {
                        "type": "integer",
                        "description": "シミュレーション期間（デフォルト：100）"
                    },
                    "learning_rate": {
                        "type": "number",
                        "description": "学習率（デフォルト：1.0）"
                    }
                },
                "required": ["network_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_periodic_optimization",
            "description": "定期発注最適化の結果を可視化します。最適化の学習曲線、コストの推移、基在庫レベルの変化をインタラクティブなグラフで表示します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "optimization_result": {
                        "type": "object",
                        "description": "optimize_periodic_inventoryの実行結果"
                    }
                },
                "required": ["optimization_result"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_safety_stock_network",
            "description": "安全在庫配置ネットワークを可視化します。optimize_safety_stock_allocationの結果をインタラクティブなネットワーク図で表示します。ノードサイズは正味補充時間（NRT）、色は保証リードタイムを表します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "optimization_result": {
                        "type": "object",
                        "description": "optimize_safety_stock_allocationの実行結果"
                    }
                },
                "required": ["optimization_result"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_eoq_incremental_discount",
            "description": "増分数量割引対応のEOQを計算します。発注量に応じて単価が段階的に安くなる場合の最適発注量を算出します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "K": {
                        "type": "number",
                        "description": "発注固定費用（円/回）"
                    },
                    "d": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "h": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "b": {
                        "type": "number",
                        "description": "品切れ費用（円/unit/日）"
                    },
                    "r": {
                        "type": "number",
                        "description": "割引率"
                    },
                    "unit_costs": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "各価格帯の単価リスト [c0, c1, c2, ...]"
                    },
                    "quantity_breaks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "各価格帯の最小発注量 [θ0, θ1, θ2, ...]"
                    }
                },
                "required": ["K", "d", "h", "b", "r", "unit_costs", "quantity_breaks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_eoq_all_units_discount",
            "description": "全単位数量割引対応のEOQを計算します。発注量に応じて全数量の単価が安くなる場合の最適発注量を算出します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "K": {
                        "type": "number",
                        "description": "発注固定費用（円/回）"
                    },
                    "d": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "h": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "b": {
                        "type": "number",
                        "description": "品切れ費用（円/unit/日）"
                    },
                    "r": {
                        "type": "number",
                        "description": "割引率"
                    },
                    "unit_costs": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "各価格帯の単価リスト [c0, c1, c2, ...]"
                    },
                    "quantity_breaks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "各価格帯の最小発注量 [θ0, θ1, θ2, ...]"
                    }
                },
                "required": ["K", "d", "h", "b", "r", "unit_costs", "quantity_breaks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visualize_eoq",
            "description": "EOQ分析の総コスト曲線を可視化します。発注量とコストの関係をグラフで表示します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "K": {
                        "type": "number",
                        "description": "発注固定費用（円/回）"
                    },
                    "d": {
                        "type": "number",
                        "description": "平均需要量（units/日）"
                    },
                    "h": {
                        "type": "number",
                        "description": "在庫保管費用（円/unit/日）"
                    },
                    "b": {
                        "type": "number",
                        "description": "品切れ費用（円/unit/日）"
                    }
                },
                "required": ["K", "d", "h", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_optimal_learning_rate_periodic",
            "description": "定期発注最適化のための最適学習率を探索します（LR Range Test）。学習率を指数的に増加させながら損失を記録し、最適な学習率を自動検出します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items_data": {
                        "type": "string",
                        "description": "品目データのJSON配列文字列"
                    },
                    "bom_data": {
                        "type": "string",
                        "description": "BOMデータのJSON配列文字列"
                    },
                    "max_iter": {
                        "type": "integer",
                        "description": "探索の最大反復回数",
                        "default": 50
                    },
                    "max_lr": {
                        "type": "number",
                        "description": "探索する最大学習率",
                        "default": 10.0
                    }
                },
                "required": ["items_data", "bom_data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_periodic_with_one_cycle",
            "description": "Fit One Cycleスケジューラを使用した高速な定期発注最適化を実行します。学習率とモメンタムを動的に調整し、効率的な収束を実現します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items_data": {
                        "type": "string",
                        "description": "品目データのJSON配列文字列"
                    },
                    "bom_data": {
                        "type": "string",
                        "description": "BOMデータのJSON配列文字列"
                    },
                    "max_iter": {
                        "type": "integer",
                        "description": "最大反復回数",
                        "default": 200
                    },
                    "max_lr": {
                        "type": "number",
                        "description": "最大学習率",
                        "default": 1.0
                    }
                },
                "required": ["items_data", "bom_data"]
            }
        }
    }
]


def execute_mcp_function(function_name: str, arguments: dict, user_id: int = None) -> dict:
    """
    MCPツール関数を実行

    Args:
        function_name: 関数名
        arguments: 引数の辞書

    Returns:
        実行結果の辞書
    """

    if function_name == "calculate_eoq":
        result = eoq(
            K=arguments["K"],
            d=arguments["d"],
            h=arguments["h"],
            b=arguments["b"],
            r=arguments.get("r", 0.0),
            c=arguments.get("c", 0.0),
            theta=arguments.get("theta", 0.0)
        )
        # eoq関数はタプル (Q*, TC*) を返す
        Q_star, TC_star = result
        return {
            "optimal_order_quantity": float(Q_star),
            "total_cost": float(TC_star),
            "parameters": {
                "fixed_order_cost": arguments["K"],
                "average_demand": arguments["d"],
                "holding_cost": arguments["h"],
                "stockout_cost": arguments["b"]
            }
        }

    elif function_name == "optimize_safety_stock_allocation":
        items = json.loads(arguments["items_data"])
        bom = json.loads(arguments["bom_data"])

        # Excelワークブック作成
        wb = make_excel_messa()

        # 品目データを追加
        ws_items = wb["品目"]
        for item in items:
            ws_items.append([
                item.get("name"),
                item.get("process_time", 1),
                item.get("max_service_time", 0),
                item.get("avg_demand"),
                item.get("demand_std"),
                item.get("holding_cost", 1),
                item.get("stockout_cost", 100),
                item.get("fixed_cost", 1000)
            ])

        # BOMデータを追加
        ws_bom = wb["部品展開表"]
        for b in bom:
            ws_bom.append([
                b.get("child"),
                b.get("parent"),
                b.get("quantity", 1)
            ])

        # 最適化実行
        try:
            # prepare_opt_for_messaは (G, ProcTime, LTUB, z, mu, sigma, h) を返す
            G, ProcTime, LTUB, z, mu, sigma, h = prepare_opt_for_messa(wb)

            # タブーサーチで最適化
            # tabu_search_for_SSAは (best_cost, best_sol, best_NRT, best_MaxLI, best_MinLT) を返す
            best_cost, best_sol_dict, best_NRT, best_MaxLI, best_MinLT = tabu_search_for_SSA(
                G, ProcTime, LTUB, z, mu, sigma, h, max_iter=100
            )

            # 結果を辞書形式にまとめる
            best_sol = {
                "best_cost": best_cost,
                "best_sol": best_sol_dict,
                "best_NRT": best_NRT,
                "best_MaxLI": best_MaxLI,
                "best_MinLT": best_MinLT
            }

            # ネットワークポジション計算
            pos = G.layout()

            # ユーザーごとにキャッシュに保存
            if user_id is not None:
                _optimization_cache[user_id] = {
                    "G": G,
                    "pos": pos,
                    "best_sol": best_sol,
                    "items": items,
                    "bom": bom
                }

            # 結果を整形
            result_data = []
            for idx, node in enumerate(G.nodes()):
                result_data.append({
                    "node": node,
                    "safety_stock": float(best_sol["best_NRT"][idx]),
                    "service_time": float(best_sol["best_MaxLI"][idx]),
                    "lead_time": float(best_sol["best_MinLT"][idx])
                })

            # posをシリアライズ可能な形式に変換
            pos_data = {int(k): list(v) for k, v in pos.items()}

            return {
                "status": "success",
                "optimization_results": result_data,
                "total_cost": float(best_sol.get("best_cost", 0)),
                "items": items,
                "bom": bom,
                "pos_data": pos_data,
                "graph_info": {
                    "num_nodes": len(G.nodes()),
                    "num_edges": len(G.edges())
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    elif function_name == "analyze_inventory_network":
        items = json.loads(arguments["items_data"])
        bom = json.loads(arguments["bom_data"])

        # Excelワークブック作成
        wb = make_excel_messa()

        # データ追加
        ws_items = wb["品目"]
        for item in items:
            ws_items.append([
                item.get("name"),
                item.get("process_time", 1),
                item.get("max_service_time", 0),
                item.get("avg_demand"),
                item.get("demand_std"),
                item.get("holding_cost", 1),
                item.get("stockout_cost", 100),
                item.get("fixed_cost", 1000)
            ])

        ws_bom = wb["部品展開表"]
        for b in bom:
            ws_bom.append([
                b.get("child"),
                b.get("parent"),
                b.get("quantity", 1)
            ])

        # ネットワーク構築
        try:
            G, ProcTime, LTUB, z, mu, sigma, h = prepare_opt_for_messa(wb)

            # ネットワーク情報抽出
            nodes_info = []
            for node in G.nodes():
                nodes_info.append({
                    "name": node,
                    "avg_demand": float(G.nodes[node].get("avgDemand", 0)),
                    "demand_std": float(G.nodes[node].get("stDevDemand", 0)),
                    "holding_cost": float(G.nodes[node].get("stageCost", 0)),
                    "process_time": float(G.nodes[node].get("stageTime", 0)),
                    "in_degree": G.in_degree(node),
                    "out_degree": G.out_degree(node)
                })

            edges_info = []
            for edge in G.edges():
                edges_info.append({
                    "from": edge[0],
                    "to": edge[1]
                })

            return {
                "status": "success",
                "network_summary": {
                    "total_nodes": len(G.nodes()),
                    "total_edges": len(G.edges()),
                    "is_dag": True
                },
                "nodes": nodes_info,
                "edges": edges_info
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    elif function_name == "visualize_last_optimization":
        # ユーザーのキャッシュを確認
        if user_id is None or user_id not in _optimization_cache:
            return {
                "status": "error",
                "message": """可視化できる最適化結果が見つかりません。

可視化できるのは、optimize_safety_stock_allocation（サプライチェーンネットワークの安全在庫最適化）の結果のみです。

以下のツールの結果は可視化できません：
- calculate_eoq（経済発注量計算）
- calculate_safety_stock（単一品目の安全在庫計算）

可視化を行うには：
1. まず optimize_safety_stock_allocation で複数品目のネットワーク最適化を実行してください
2. その後、このツールで結果を可視化できます

複数の品目データとBOM（部品表）を用意して、optimize_safety_stock_allocation を実行してください。"""
            }

        try:
            # キャッシュから取得
            cache = _optimization_cache[user_id]
            G = cache["G"]
            pos = cache["pos"]
            best_sol = cache["best_sol"]

            # 可視化
            fig = draw_graph_for_SSA(G, pos, best_sol["best_NRT"], best_sol["best_MaxLI"], best_sol["best_MinLT"])

            # HTMLをメモリ上で生成して、キャッシュに保存
            html_content = pio.to_html(fig, include_plotlyjs='cdn')

            # UUIDベースのviz_idを生成
            viz_id = str(uuid.uuid4())

            # キャッシュにHTML保存（後でエンドポイントから取得）
            _optimization_cache[user_id][viz_id] = html_content

            # 可視化用URLを生成
            viz_url = f"/api/visualization/{viz_id}"

            return {
                "status": "success",
                "visualization_id": viz_id,
                "visualization_url": viz_url,
                "message": "可視化が完成しました。リンクをクリックして確認してください。",
                "total_cost": float(best_sol.get("best_cost", 0))
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"可視化エラー: {str(e)}"
            }

    elif function_name == "generate_sample_data":
        complexity = arguments.get("complexity", "simple")

        # サンプルデータパターン定義
        sample_patterns = {
            "simple": {
                "description": "シンプルな3品目の直列サプライチェーン（製品→部品→原材料）",
                "items": [
                    {
                        "name": "製品A",
                        "process_time": 2,
                        "max_service_time": 0,
                        "avg_demand": 100,
                        "demand_std": 20,
                        "holding_cost": 5,
                        "stockout_cost": 100,
                        "fixed_cost": 10000
                    },
                    {
                        "name": "部品B",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 200,
                        "demand_std": 30,
                        "holding_cost": 3,
                        "stockout_cost": 80,
                        "fixed_cost": 8000
                    },
                    {
                        "name": "原材料C",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 300,
                        "demand_std": 40,
                        "holding_cost": 2,
                        "stockout_cost": 50,
                        "fixed_cost": 5000
                    }
                ],
                "bom": [
                    {"child": "部品B", "parent": "製品A", "quantity": 2},
                    {"child": "原材料C", "parent": "部品B", "quantity": 1}
                ]
            },
            "standard": {
                "description": "標準的な5品目のサプライチェーンネットワーク（製品が複数の部品を使用）",
                "items": [
                    {
                        "name": "完成品X",
                        "process_time": 3,
                        "max_service_time": 0,
                        "avg_demand": 50,
                        "demand_std": 15,
                        "holding_cost": 10,
                        "stockout_cost": 150,
                        "fixed_cost": 15000
                    },
                    {
                        "name": "サブアセンブリY",
                        "process_time": 2,
                        "max_service_time": 0,
                        "avg_demand": 100,
                        "demand_std": 25,
                        "holding_cost": 6,
                        "stockout_cost": 100,
                        "fixed_cost": 10000
                    },
                    {
                        "name": "部品Z1",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 150,
                        "demand_std": 30,
                        "holding_cost": 4,
                        "stockout_cost": 80,
                        "fixed_cost": 7000
                    },
                    {
                        "name": "部品Z2",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 150,
                        "demand_std": 30,
                        "holding_cost": 4,
                        "stockout_cost": 80,
                        "fixed_cost": 7000
                    },
                    {
                        "name": "原材料M",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 400,
                        "demand_std": 50,
                        "holding_cost": 2,
                        "stockout_cost": 40,
                        "fixed_cost": 4000
                    }
                ],
                "bom": [
                    {"child": "サブアセンブリY", "parent": "完成品X", "quantity": 2},
                    {"child": "部品Z1", "parent": "完成品X", "quantity": 1},
                    {"child": "部品Z2", "parent": "サブアセンブリY", "quantity": 1},
                    {"child": "原材料M", "parent": "部品Z1", "quantity": 2},
                    {"child": "原材料M", "parent": "部品Z2", "quantity": 1}
                ]
            },
            "complex": {
                "description": "複雑な8品目のマルチエシュロンサプライチェーンネットワーク",
                "items": [
                    {
                        "name": "最終製品P1",
                        "process_time": 3,
                        "max_service_time": 0,
                        "avg_demand": 40,
                        "demand_std": 12,
                        "holding_cost": 12,
                        "stockout_cost": 200,
                        "fixed_cost": 20000
                    },
                    {
                        "name": "最終製品P2",
                        "process_time": 3,
                        "max_service_time": 0,
                        "avg_demand": 35,
                        "demand_std": 10,
                        "holding_cost": 12,
                        "stockout_cost": 200,
                        "fixed_cost": 20000
                    },
                    {
                        "name": "アセンブリA1",
                        "process_time": 2,
                        "max_service_time": 0,
                        "avg_demand": 80,
                        "demand_std": 20,
                        "holding_cost": 7,
                        "stockout_cost": 120,
                        "fixed_cost": 12000
                    },
                    {
                        "name": "アセンブリA2",
                        "process_time": 2,
                        "max_service_time": 0,
                        "avg_demand": 70,
                        "demand_std": 18,
                        "holding_cost": 7,
                        "stockout_cost": 120,
                        "fixed_cost": 12000
                    },
                    {
                        "name": "部品C1",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 180,
                        "demand_std": 35,
                        "holding_cost": 4,
                        "stockout_cost": 80,
                        "fixed_cost": 7000
                    },
                    {
                        "name": "部品C2",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 160,
                        "demand_std": 30,
                        "holding_cost": 4,
                        "stockout_cost": 80,
                        "fixed_cost": 7000
                    },
                    {
                        "name": "原材料R1",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 500,
                        "demand_std": 60,
                        "holding_cost": 2,
                        "stockout_cost": 40,
                        "fixed_cost": 4000
                    },
                    {
                        "name": "原材料R2",
                        "process_time": 1,
                        "max_service_time": 0,
                        "avg_demand": 450,
                        "demand_std": 55,
                        "holding_cost": 2,
                        "stockout_cost": 40,
                        "fixed_cost": 4000
                    }
                ],
                "bom": [
                    {"child": "アセンブリA1", "parent": "最終製品P1", "quantity": 2},
                    {"child": "アセンブリA2", "parent": "最終製品P2", "quantity": 2},
                    {"child": "部品C1", "parent": "アセンブリA1", "quantity": 1},
                    {"child": "部品C2", "parent": "アセンブリA1", "quantity": 1},
                    {"child": "部品C1", "parent": "アセンブリA2", "quantity": 1},
                    {"child": "部品C2", "parent": "アセンブリA2", "quantity": 1},
                    {"child": "原材料R1", "parent": "部品C1", "quantity": 3},
                    {"child": "原材料R2", "parent": "部品C2", "quantity": 2},
                    {"child": "原材料R1", "parent": "部品C2", "quantity": 1}
                ]
            }
        }

        if complexity not in sample_patterns:
            return {
                "status": "error",
                "message": f"無効な複雑さレベル: {complexity}. simple, standard, complex のいずれかを指定してください。"
            }

        pattern = sample_patterns[complexity]

        return {
            "status": "success",
            "complexity": complexity,
            "description": pattern["description"],
            "items_count": len(pattern["items"]),
            "bom_count": len(pattern["bom"]),
            "items_data": pattern["items"],
            "bom_data": pattern["bom"],
            "data_explanation": {
                "items_data": "品目データ：各品目の特性（処理時間、需要、コストなど）を定義します",
                "fields": {
                    "name": "品目名",
                    "process_time": "処理時間（日）",
                    "max_service_time": "最大サービス時間（日）",
                    "avg_demand": "平均需要量（units/日）",
                    "demand_std": "需要の標準偏差",
                    "holding_cost": "在庫保管費用（円/unit/日）",
                    "stockout_cost": "品切れ費用（円/unit/日）",
                    "fixed_cost": "固定発注費用（円/回）"
                },
                "bom_data": "BOM（部品表）：品目間の親子関係と必要数量を定義します",
                "bom_fields": {
                    "child": "子品目（使用される部品）",
                    "parent": "親品目（製品）",
                    "quantity": "親1個を作るのに必要な子の数量"
                }
            },
            "usage": f"このデータをoptimize_safety_stock_allocationツールに渡して最適化を実行できます。その後、visualize_last_optimizationで結果を可視化できます。"
        }

    elif function_name == "simulate_qr_policy":
        # (Q,R)方策のシミュレーション
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            Q = arguments["Q"]
            R = arguments["R"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            # シミュレーション実行
            # simulate_inventory関数は(cost_array, inventory_array)のタプルを返す
            cost_array, inventory_array = simulate_inventory(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                Q=Q,
                R=R,
                b=b,
                h=h,
                fc=fc
            )

            # コストの平均を計算
            avg_cost = float(cost_array.mean())

            return {
                "status": "success",
                "policy_type": "(Q,R)方策",
                "parameters": {
                    "order_quantity_Q": float(Q),
                    "reorder_point_R": float(R),
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "lead_time": int(LT),
                    "holding_cost": float(h),
                    "stockout_cost": float(b),
                    "fixed_cost": float(fc)
                },
                "simulation_results": {
                    "average_cost_per_period": avg_cost,
                    "n_samples": n_samples,
                    "n_periods": n_periods
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"シミュレーションエラー: {str(e)}"
            }

    elif function_name == "optimize_qr_policy":
        # (Q,R)方策の最適化
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            # 最適化実行
            # optimize_qr関数は (最適Q, 最適R) の2要素タプルを返す
            optimal_Q, optimal_R = optimize_qr(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                b=b,
                h=h,
                fc=fc
            )

            # 最適パラメータでシミュレーションしてコストを計算
            cost_array, _ = simulate_inventory(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                Q=optimal_Q,
                R=optimal_R,
                b=b,
                h=h,
                fc=fc
            )
            min_cost = float(cost_array.mean())

            return {
                "status": "success",
                "policy_type": "(Q,R)方策の最適化",
                "optimal_parameters": {
                    "optimal_order_quantity_Q": float(optimal_Q),
                    "optimal_reorder_point_R": float(optimal_R)
                },
                "optimization_results": {
                    "minimum_average_cost": min_cost,
                    "n_samples": n_samples,
                    "n_periods": n_periods
                },
                "input_parameters": {
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "lead_time": int(LT),
                    "holding_cost": float(h),
                    "stockout_cost": float(b),
                    "fixed_cost": float(fc)
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"最適化エラー: {str(e)}"
            }

    elif function_name == "simulate_ss_policy":
        # (s,S)方策のシミュレーション
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            s = arguments["s"]
            S = arguments["S"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            # シミュレーション実行（Sパラメータを指定）
            cost_array, inventory_array = simulate_inventory(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                Q=None,  # (s,S)方策ではQは使用しない
                R=s,     # 発注点sをRとして渡す
                b=b,
                h=h,
                fc=fc,
                S=S      # 基在庫レベル
            )

            # コストの平均を計算
            avg_cost = float(cost_array.mean())

            return {
                "status": "success",
                "policy_type": "(s,S)方策",
                "parameters": {
                    "reorder_point_s": float(s),
                    "base_stock_level_S": float(S),
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "lead_time": int(LT),
                    "holding_cost": float(h),
                    "stockout_cost": float(b),
                    "fixed_cost": float(fc)
                },
                "simulation_results": {
                    "average_cost_per_period": avg_cost,
                    "n_samples": n_samples,
                    "n_periods": n_periods
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"シミュレーションエラー: {str(e)}"
            }

    elif function_name == "optimize_ss_policy":
        # (s,S)方策の最適化
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            # 最適化実行
            # optimize_ss関数は (最適s, 最適S) の2要素タプルを返す
            optimal_s, optimal_S = optimize_ss(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                b=b,
                h=h,
                fc=fc
            )

            # 最適パラメータでシミュレーションしてコストを計算
            cost_array, _ = simulate_inventory(
                n_samples=n_samples,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                Q=None,  # (s,S)方策ではQは使用しない
                R=optimal_s,  # 発注点sをRとして渡す
                b=b,
                h=h,
                fc=fc,
                S=optimal_S  # 基在庫レベル
            )
            min_cost = float(cost_array.mean())

            return {
                "status": "success",
                "policy_type": "(s,S)方策の最適化",
                "optimal_parameters": {
                    "optimal_reorder_point_s": float(optimal_s),
                    "optimal_base_stock_level_S": float(optimal_S)
                },
                "optimization_results": {
                    "minimum_average_cost": min_cost,
                    "n_samples": n_samples,
                    "n_periods": n_periods
                },
                "input_parameters": {
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "lead_time": int(LT),
                    "holding_cost": float(h),
                    "stockout_cost": float(b),
                    "fixed_cost": float(fc)
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"最適化エラー: {str(e)}"
            }

    elif function_name == "calculate_wagner_whitin":
        # Wagner-Whitinアルゴリズムによる動的ロットサイジング
        try:
            demand = arguments["demand"]
            fc = arguments["fixed_cost"]
            h = arguments["holding_cost"]
            vc = arguments.get("variable_cost", 0.0)

            # ww関数は (total_cost, order_schedule) のタプルを返す
            total_cost, order_schedule = ww(
                demand=demand,
                fc=fc,
                vc=vc,
                h=h
            )

            # 発注期を特定
            order_periods = [i for i, qty in enumerate(order_schedule) if qty > 0]

            return {
                "status": "success",
                "algorithm": "Wagner-Whitin動的ロットサイジング",
                "results": {
                    "total_cost": float(total_cost),
                    "order_schedule": [float(x) for x in order_schedule],
                    "order_periods": order_periods,
                    "number_of_orders": len(order_periods)
                },
                "input_parameters": {
                    "demand": demand,
                    "fixed_cost": float(fc),
                    "holding_cost": float(h),
                    "variable_cost": float(vc)
                },
                "summary": f"総コスト: {float(total_cost):.2f}円、発注回数: {len(order_periods)}回"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Wagner-Whitin計算エラー: {str(e)}"
            }

    elif function_name == "analyze_demand_pattern":
        # 需要パターンの統計分析
        try:
            demand = np.array(arguments["demand"])

            # 基本統計量
            mean_demand = float(np.mean(demand))
            std_demand = float(np.std(demand, ddof=1))
            cv = std_demand / mean_demand if mean_demand > 0 else 0
            min_demand = float(np.min(demand))
            max_demand = float(np.max(demand))
            median_demand = float(np.median(demand))

            # 需要パターンの判定
            if cv < 0.2:
                pattern_type = "非常に安定"
                recommendation = "定量発注方式(EOQ, (Q,R)方策)が適しています"
            elif cv < 0.5:
                pattern_type = "安定"
                recommendation = "(Q,R)方策または(s,S)方策が適しています"
            elif cv < 1.0:
                pattern_type = "中程度の変動"
                recommendation = "(s,S)方策または定期発注方式が適しています"
            else:
                pattern_type = "高変動"
                recommendation = "安全在庫を多めに設定するか、定期発注方式を検討してください"

            return {
                "status": "success",
                "analysis_type": "需要パターン分析",
                "statistics": {
                    "mean": mean_demand,
                    "standard_deviation": std_demand,
                    "coefficient_of_variation": cv,
                    "min": min_demand,
                    "max": max_demand,
                    "median": median_demand,
                    "sample_size": len(demand)
                },
                "pattern_assessment": {
                    "pattern_type": pattern_type,
                    "variability_level": cv,
                    "recommendation": recommendation
                },
                "input_data": {
                    "demand": [float(x) for x in demand]
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"需要分析エラー: {str(e)}"
            }

    elif function_name == "compare_inventory_policies":
        # 複数の在庫方策を比較
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            results = {}

            # 1. EOQ方策
            Q_eoq, TC_eoq = eoq(K=fc, d=mu, h=h, b=b, r=0, c=0, theta=0)
            results["EOQ"] = {
                "optimal_Q": float(Q_eoq),
                "annual_cost": float(TC_eoq),
                "policy_description": "定量発注方式（固定発注量）"
            }

            # 2. (Q,R)方策
            Q_qr, R_qr = optimize_qr(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
            )
            cost_qr, _ = simulate_inventory(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT,
                Q=Q_qr, R=R_qr, b=b, h=h, fc=fc
            )
            results["QR_policy"] = {
                "optimal_Q": float(Q_qr),
                "optimal_R": float(R_qr),
                "average_cost": float(cost_qr.mean()),
                "policy_description": "(Q,R)方策（定量発注点方式）"
            }

            # 3. (s,S)方策
            s_ss, S_ss = optimize_ss(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
            )
            cost_ss, _ = simulate_inventory(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT,
                Q=None, R=s_ss, b=b, h=h, fc=fc, S=S_ss
            )
            results["sS_policy"] = {
                "optimal_s": float(s_ss),
                "optimal_S": float(S_ss),
                "average_cost": float(cost_ss.mean()),
                "policy_description": "(s,S)方策（発注点・基在庫方式）"
            }

            # 最適方策を決定
            costs = {
                "EOQ": results["EOQ"]["annual_cost"] / 365,  # 日あたりに変換
                "QR_policy": results["QR_policy"]["average_cost"],
                "sS_policy": results["sS_policy"]["average_cost"]
            }
            best_policy = min(costs, key=costs.get)

            return {
                "status": "success",
                "comparison_type": "在庫方策の比較分析",
                "policies": results,
                "recommendation": {
                    "best_policy": best_policy,
                    "best_cost": float(costs[best_policy]),
                    "cost_comparison": {k: float(v) for k, v in costs.items()},
                    "reasoning": f"{best_policy}が最も低コスト（1日あたり{costs[best_policy]:.2f}円）"
                },
                "input_parameters": {
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "lead_time": int(LT),
                    "holding_cost": float(h),
                    "stockout_cost": float(b),
                    "fixed_cost": float(fc)
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"方策比較エラー: {str(e)}"
            }

    elif function_name == "calculate_safety_stock":
        # 安全在庫の計算
        try:
            mu = arguments.get("mu")
            sigma = arguments.get("sigma")
            # lead_timeとLTの両方に対応
            LT = arguments.get("lead_time") or arguments.get("LT")
            service_level = arguments.get("service_level")
            h = arguments.get("holding_cost", None)

            # 必須パラメータのチェック
            if mu is None or sigma is None or LT is None or service_level is None:
                missing = []
                if mu is None: missing.append("mu (平均需要)")
                if sigma is None: missing.append("sigma (標準偏差)")
                if LT is None: missing.append("lead_time/LT (リードタイム)")
                if service_level is None: missing.append("service_level (サービスレベル)")
                return {
                    "status": "error",
                    "message": f"必須パラメータが不足しています: {', '.join(missing)}",
                    "received_arguments": arguments
                }

            # リードタイム需要の平均と標準偏差
            mu_LT = mu * LT
            sigma_LT = sigma * np.sqrt(LT)

            # サービスレベルに対応するz値
            z = stats.norm.ppf(service_level)

            # 安全在庫
            safety_stock = z * sigma_LT

            # 再発注点（ROP）
            reorder_point = mu_LT + safety_stock

            # 年間在庫保持コスト（オプション）
            annual_holding_cost = None
            if h is not None:
                annual_holding_cost = float(safety_stock * h * 365)

            result = {
                "status": "success",
                "calculation_type": "安全在庫計算",
                "results": {
                    "safety_stock": float(safety_stock),
                    "reorder_point": float(reorder_point),
                    "lead_time_demand_mean": float(mu_LT),
                    "lead_time_demand_std": float(sigma_LT),
                    "z_value": float(z)
                },
                "service_level": {
                    "target": float(service_level),
                    "percentage": f"{service_level*100:.1f}%",
                    "meaning": f"需要の{service_level*100:.1f}%をカバー"
                },
                "input_parameters": {
                    "daily_demand_mean": float(mu),
                    "daily_demand_std": float(sigma),
                    "lead_time_days": int(LT)
                }
            }

            if annual_holding_cost is not None:
                result["cost_analysis"] = {
                    "annual_holding_cost": annual_holding_cost,
                    "daily_holding_cost": float(safety_stock * h)
                }

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"安全在庫計算エラー: {str(e)}"
            }

    elif function_name == "visualize_inventory_simulation":
        # シミュレーション結果の可視化
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            policy_type = arguments["policy_type"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_periods = arguments.get("n_periods", 100)

            # パラメータ取得
            if policy_type == "QR":
                Q = arguments.get("Q")
                R = arguments.get("R")
                if Q is None or R is None:
                    return {
                        "status": "error",
                        "message": "(Q,R)方策にはQとRのパラメータが必要です"
                    }
                S = None
                s = R
            else:  # sS
                s = arguments.get("s")
                S = arguments.get("S")
                if s is None or S is None:
                    return {
                        "status": "error",
                        "message": "(s,S)方策にはsとSのパラメータが必要です"
                    }
                Q = None
                R = s

            # シミュレーション実行（1サンプルのみ）
            cost_array, inventory_array = simulate_inventory(
                n_samples=1,
                n_periods=n_periods,
                mu=mu,
                sigma=sigma,
                LT=LT,
                Q=Q,
                R=R,
                b=b,
                h=h,
                fc=fc,
                S=S
            )

            # グラフ作成
            inventory_levels = inventory_array[0, :]  # 最初のサンプル
            periods = list(range(len(inventory_levels)))

            fig = go.Figure()

            # 在庫レベルの推移
            fig.add_trace(go.Scatter(
                x=periods,
                y=inventory_levels,
                mode='lines+markers',
                name='在庫レベル',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ))

            # 発注点の表示
            if policy_type == "QR":
                fig.add_hline(y=R, line_dash="dash", line_color="red",
                             annotation_text=f"発注点 R={R:.1f}",
                             annotation_position="right")
            else:
                fig.add_hline(y=s, line_dash="dash", line_color="red",
                             annotation_text=f"発注点 s={s:.1f}",
                             annotation_position="right")
                fig.add_hline(y=S, line_dash="dash", line_color="green",
                             annotation_text=f"基在庫レベル S={S:.1f}",
                             annotation_position="right")

            # 品切れ領域の表示
            fig.add_hrect(y0=-1, y1=0, fillcolor="red", opacity=0.2,
                         annotation_text="品切れ領域", annotation_position="top left")

            fig.update_layout(
                title=f"{policy_type}方策の在庫シミュレーション",
                xaxis_title="期間（日）",
                yaxis_title="在庫レベル（units）",
                hovermode='x unified',
                template="plotly_white"
            )

            # HTMLとして保存
            viz_id = str(uuid.uuid4())
            html_content = fig.to_html(include_plotlyjs='cdn')

            # キャッシュに保存
            if user_id:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = html_content

            return {
                "status": "success",
                "visualization_type": "在庫シミュレーション可視化",
                "visualization_id": viz_id,
                "policy_info": {
                    "policy_type": policy_type,
                    "parameters": {
                        "Q": float(Q) if Q else None,
                        "R": float(R) if R else None,
                        "s": float(s) if s else None,
                        "S": float(S) if S else None
                    }
                },
                "simulation_stats": {
                    "average_inventory": float(inventory_levels.mean()),
                    "max_inventory": float(inventory_levels.max()),
                    "min_inventory": float(inventory_levels.min()),
                    "stockouts": int((inventory_levels < 0).sum()),
                    "average_cost_per_period": float(cost_array.mean())
                },
                "message": f"可視化を生成しました。visualization_idを使用して表示できます: {viz_id}"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"可視化エラー: {str(e)}"
            }

    elif function_name == "find_best_distribution":
        # 最適需要分布の自動選択
        try:
            demand_data = np.array(arguments["demand"])

            # best_distribution関数を実行
            # 戻り値: (fig, distribution, dist_name, params)
            fig, dist_obj, dist_name, params = best_distribution(demand_data)

            # UUIDベースのviz_idを生成
            viz_id = str(uuid.uuid4())

            # HTMLとして保存
            html_content = fig.to_html(include_plotlyjs='cdn')

            # キャッシュに保存
            if user_id:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = html_content

            return {
                "status": "success",
                "distribution_analysis": "最適需要分布フィッティング",
                "best_distribution": dist_name,
                "parameters": {
                    "param1": float(params[0]) if len(params) > 0 else None,
                    "param2": float(params[1]) if len(params) > 1 else None,
                    "param3": float(params[2]) if len(params) > 2 else None
                },
                "visualization_id": viz_id,
                "message": f"最適分布は {dist_name} です。フィッティング結果を可視化しました。",
                "input_data": {
                    "sample_size": len(demand_data),
                    "mean": float(demand_data.mean()),
                    "std": float(demand_data.std())
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"分布フィッティングエラー: {str(e)}"
            }

    elif function_name == "visualize_demand_histogram":
        # 需要ヒストグラム可視化
        try:
            demand_data = np.array(arguments["demand"])
            nbins = arguments.get("nbins", 30)

            # best_histogram関数を実行
            # 戻り値: (fig, stats_dict)
            fig, stats = best_histogram(demand_data, nbins=nbins)

            # UUIDベースのviz_idを生成
            viz_id = str(uuid.uuid4())

            # HTMLとして保存
            html_content = fig.to_html(include_plotlyjs='cdn')

            # キャッシュに保存
            if user_id:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = html_content

            # 基本統計量を計算
            mean_val = float(demand_data.mean())
            median_val = float(np.median(demand_data))
            std_val = float(demand_data.std())
            min_val = float(demand_data.min())
            max_val = float(demand_data.max())

            return {
                "status": "success",
                "visualization_type": "需要ヒストグラム",
                "statistics": {
                    "mean": mean_val,
                    "median": median_val,
                    "standard_deviation": std_val,
                    "min": min_val,
                    "max": max_val,
                    "sample_size": len(demand_data),
                    "nbins": nbins
                },
                "visualization_id": viz_id,
                "message": "需要データのヒストグラムを作成しました。"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"ヒストグラム作成エラー: {str(e)}"
            }

    elif function_name == "compare_inventory_costs_visual":
        # 在庫方策のコスト比較可視化
        try:
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            h = arguments["holding_cost"]
            b = arguments["stockout_cost"]
            fc = arguments["fixed_cost"]
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)

            # 3つの方策を計算
            results = {}

            # 1. EOQ
            Q_eoq, TC_eoq = eoq(K=fc, d=mu, h=h, b=b, r=0, c=0, theta=0)
            results["EOQ"] = float(TC_eoq / 365)  # 日あたりに変換

            # 2. (Q,R)方策
            Q_qr, R_qr = optimize_qr(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
            )
            cost_qr, _ = simulate_inventory(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT,
                Q=Q_qr, R=R_qr, b=b, h=h, fc=fc
            )
            results["(Q,R)方策"] = float(cost_qr.mean())

            # 3. (s,S)方策
            s_ss, S_ss = optimize_ss(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
            )
            cost_ss, _ = simulate_inventory(
                n_samples=n_samples, n_periods=n_periods,
                mu=mu, sigma=sigma, LT=LT,
                Q=None, R=s_ss, b=b, h=h, fc=fc, S=S_ss
            )
            results["(s,S)方策"] = float(cost_ss.mean())

            # Plotlyで棒グラフ作成
            fig = go.Figure(data=[
                go.Bar(
                    x=list(results.keys()),
                    y=list(results.values()),
                    text=[f"{v:.2f}円" for v in results.values()],
                    textposition='auto',
                )
            ])

            fig.update_layout(
                title="在庫方策のコスト比較",
                xaxis_title="在庫方策",
                yaxis_title="平均コスト（円/日）",
                template="plotly_white"
            )

            # UUIDベースのviz_idを生成
            viz_id = str(uuid.uuid4())

            # HTMLとして保存
            html_content = fig.to_html(include_plotlyjs='cdn')

            # キャッシュに保存
            if user_id:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = html_content

            # 最適方策を決定
            best_policy = min(results, key=results.get)

            return {
                "status": "success",
                "visualization_type": "コスト比較グラフ",
                "costs": results,
                "recommendation": {
                    "best_policy": best_policy,
                    "best_cost": results[best_policy],
                    "savings_vs_worst": max(results.values()) - results[best_policy]
                },
                "visualization_id": viz_id,
                "message": f"{best_policy}が最もコスト効率が良いです（{results[best_policy]:.2f}円/日）"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"コスト比較可視化エラー: {str(e)}"
            }

    elif function_name == "simulate_base_stock_policy":
        # ベースストック方策シミュレーション
        try:
            demand = np.array(arguments["demand"])
            S = arguments.get("base_stock_level")
            if S is None:
                return {
                    "status": "error",
                    "message": "base_stock_level（ベースストックレベル）パラメータが必要です。例: base_stock_level=50"
                }
            LT = arguments.get("lead_time")
            if LT is None:
                return {
                    "status": "error",
                    "message": "lead_time（リードタイム）パラメータが必要です。例: lead_time=3"
                }
            capacity = arguments.get("capacity")
            if capacity is None:
                return {
                    "status": "error",
                    "message": "capacity（生産能力）パラメータが必要です。例: capacity=1000"
                }
            h = arguments.get("holding_cost")
            if h is None:
                return {
                    "status": "error",
                    "message": "holding_cost（在庫保管費用）パラメータが必要です。例: holding_cost=1.0"
                }
            b = arguments.get("stockout_cost")
            if b is None:
                return {
                    "status": "error",
                    "message": "stockout_cost（品切れ費用）パラメータが必要です。例: stockout_cost=100.0"
                }
            n_samples = arguments.get("n_samples", 5)
            n_periods = len(demand) if len(demand) < 1000 else 100

            # 修正版関数を実行
            dC, total_cost, I = base_stock_simulation_fixed(
                n_samples=n_samples,
                n_periods=n_periods,
                demand=demand,
                capacity=capacity,
                LT=LT,
                b=b,
                h=h,
                S=S
            )

            # 在庫統計
            avg_inventory = float(I[I > 0].mean()) if (I > 0).any() else 0.0
            stockout_periods = int((I < 0).sum())
            stockout_rate = float(stockout_periods / (n_samples * n_periods))

            return {
                "status": "success",
                "policy_type": "ベースストック方策",
                "parameters": {
                    "base_stock_level_S": float(S),
                    "lead_time": int(LT),
                    "capacity": float(capacity),
                    "holding_cost": float(h),
                    "stockout_cost": float(b)
                },
                "simulation_results": {
                    "total_cost_per_period": total_cost,
                    "derivative_dC_dS": float(dC),
                    "n_samples": n_samples,
                    "n_periods": n_periods
                },
                "inventory_statistics": {
                    "average_inventory": avg_inventory,
                    "stockout_periods": stockout_periods,
                    "stockout_rate": stockout_rate,
                    "final_inventory": float(I[0, -1])
                },
                "message": f"ベースストック方策のシミュレーション完了。総コスト: {total_cost:.2f}円/期"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"ベースストックシミュレーションエラー: {str(e)}"
            }

    elif function_name == "calculate_base_stock_levels":
        # ベースストックレベル計算
        try:
            nodes = arguments["nodes"]
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            service_level = arguments["service_level"]

            # サービス水準からz値を計算
            from scipy.stats import norm
            z = norm.ppf(service_level)

            # ノード辞書を作成
            LT_dict = {node["name"]: node["lead_time"] for node in nodes}

            # 修正版関数を実行
            S_dict, ELT_dict = initial_base_stock_level_fixed(
                LT_dict=LT_dict,
                mu=mu,
                z=z,
                sigma=sigma
            )

            # 結果を整形
            node_results = []
            for node in nodes:
                name = node["name"]
                node_results.append({
                    "node_name": name,
                    "lead_time": LT_dict[name],
                    "echelon_lead_time": ELT_dict[name],
                    "base_stock_level": float(S_dict[name]),
                    "safety_stock": float(S_dict[name] - mu * ELT_dict[name])
                })

            return {
                "status": "success",
                "calculation_type": "初期ベースストックレベル計算",
                "parameters": {
                    "average_demand": float(mu),
                    "demand_std_dev": float(sigma),
                    "service_level": float(service_level),
                    "z_value": float(z)
                },
                "node_results": node_results,
                "total_nodes": len(nodes),
                "message": f"{len(nodes)}ノードのベースストックレベルを計算しました（サービス水準: {service_level*100:.0f}%）"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"ベースストックレベル計算エラー: {str(e)}"
            }

    elif function_name == "forecast_demand":
        # 需要予測
        try:
            demand_history = arguments["demand_history"]
            forecast_periods = arguments.get("forecast_periods", 7)
            method = arguments.get("method", "exponential_smoothing")
            confidence_level = arguments.get("confidence_level", 0.95)

            # オプションパラメータ
            kwargs = {}
            if "window" in arguments:
                kwargs["window"] = arguments["window"]
            if "alpha" in arguments:
                kwargs["alpha"] = arguments["alpha"]

            # 予測実行
            result = forecast_demand_util(
                demand_history=demand_history,
                forecast_periods=forecast_periods,
                method=method,
                confidence_level=confidence_level,
                **kwargs
            )

            return {
                "status": "success",
                "forecast_type": "需要予測",
                "forecast": result["forecast"],
                "lower_bound": result["lower_bound"],
                "upper_bound": result["upper_bound"],
                "confidence_level": result["confidence_level"],
                "method_info": result["method_info"],
                "historical_stats": result["historical_stats"],
                "forecast_periods": forecast_periods,
                "message": f"{result['method_info']['method']}により{forecast_periods}期間の需要予測を行いました"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"需要予測エラー: {str(e)}"
            }

    elif function_name == "visualize_forecast":
        # 需要予測の可視化
        try:
            demand_history = arguments["demand_history"]
            forecast_periods = arguments.get("forecast_periods", 7)
            method = arguments.get("method", "exponential_smoothing")
            confidence_level = arguments.get("confidence_level", 0.95)

            # オプションパラメータ
            kwargs = {}
            if "window" in arguments:
                kwargs["window"] = arguments["window"]
            if "alpha" in arguments:
                kwargs["alpha"] = arguments["alpha"]

            # 予測実行
            result = forecast_demand_util(
                demand_history=demand_history,
                forecast_periods=forecast_periods,
                method=method,
                confidence_level=confidence_level,
                **kwargs
            )

            # 時系列データの準備
            n_history = len(demand_history)
            history_x = list(range(1, n_history + 1))
            forecast_x = list(range(n_history + 1, n_history + forecast_periods + 1))

            # Plotlyグラフ作成
            fig = go.Figure()

            # 過去データ
            fig.add_trace(go.Scatter(
                x=history_x,
                y=demand_history,
                mode='lines+markers',
                name='過去の需要',
                line=dict(color='blue', width=2),
                marker=dict(size=6)
            ))

            # 予測値
            fig.add_trace(go.Scatter(
                x=forecast_x,
                y=result["forecast"],
                mode='lines+markers',
                name='予測値',
                line=dict(color='red', width=2, dash='dash'),
                marker=dict(size=6, symbol='diamond')
            ))

            # 信頼区間（帯グラフ）
            fig.add_trace(go.Scatter(
                x=forecast_x + forecast_x[::-1],
                y=result["upper_bound"] + result["lower_bound"][::-1],
                fill='toself',
                fillcolor='rgba(255,0,0,0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name=f'{int(confidence_level*100)}%信頼区間',
                showlegend=True
            ))

            # レイアウト設定
            method_name = result["method_info"]["method"]
            fig.update_layout(
                title=f"需要予測結果（{method_name}）",
                xaxis_title="期間",
                yaxis_title="需要量",
                template="plotly_white",
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )

            # 境界線を追加（過去と未来の境界）
            fig.add_vline(
                x=n_history + 0.5,
                line_dash="dot",
                line_color="gray",
                annotation_text="予測開始",
                annotation_position="top"
            )

            # UUIDベースのviz_idを生成
            viz_id = str(uuid.uuid4())

            # HTMLとして保存
            html_content = fig.to_html(include_plotlyjs='cdn')

            # キャッシュに保存
            if user_id:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = html_content

            return {
                "status": "success",
                "visualization_type": "需要予測グラフ",
                "visualization_id": viz_id,
                "method": method_name,
                "forecast_summary": {
                    "forecast_periods": forecast_periods,
                    "average_forecast": float(np.mean(result["forecast"])),
                    "historical_average": result["historical_stats"]["mean"]
                },
                "message": f"{method_name}による需要予測を可視化しました"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"需要予測可視化エラー: {str(e)}"
            }

    elif function_name == "optimize_periodic_inventory":
        try:
            network_data = arguments["network_data"]
            max_iter = arguments.get("max_iter", 100)
            n_samples = arguments.get("n_samples", 10)
            n_periods = arguments.get("n_periods", 100)
            learning_rate = arguments.get("learning_rate", 1.0)

            # BOMデータのカラム名を標準形式に変換とデフォルト値設定
            connections = network_data.get("connections", [])
            for bom in connections:
                # 'quantity' を 'units' に変換
                if 'quantity' in bom and 'units' not in bom:
                    bom['units'] = bom.pop('quantity')
                # デフォルト値の設定
                if 'units' not in bom:
                    bom['units'] = 1
                if 'allocation' not in bom:
                    bom['allocation'] = 1.0

            # stagesデータのカラム名変換
            stages = network_data.get("stages", [])
            for item in stages:
                if 'avg_demand' in item and 'average_demand' not in item:
                    item['average_demand'] = item.pop('avg_demand')
                if 'demand_std' in item and 'sigma' not in item:
                    item['sigma'] = item.pop('demand_std')
                if 'holding_cost' in item and 'h' not in item:
                    item['h'] = item.pop('holding_cost')
                if 'stockout_cost' in item and 'b' not in item:
                    item['b'] = item.pop('stockout_cost')
                # デフォルト値の設定
                if 'capacity' not in item:
                    item['capacity'] = 10000
                if 'net_replenishment_time' not in item:
                    item['net_replenishment_time'] = item.get('process_time', 1)

            # stage_dfとbom_dfを準備
            stage_df, bom_df = prepare_stage_bom_data(network_data)

            # 最適化実行
            result = optimize_periodic_util(
                stage_df=stage_df,
                bom_df=bom_df,
                max_iter=max_iter,
                n_samples=n_samples,
                n_periods=n_periods,
                learning_rate=learning_rate
            )

            # DataFrameをJSONシリアライズ可能な形式に変換
            stage_result = result["stage_df"].to_dict(orient="records")

            return {
                "status": "success",
                "optimization_type": "定期発注最適化",
                "best_cost": result["best_cost"],
                "converged": result["converged"],
                "iterations": result["final_iteration"],
                "stages": stage_result,
                "echelon_lead_time": result["echelon_lead_time"],
                "optimization_history": result["optimization_history"],
                "message": f"最適化完了: {result['final_iteration']}回の反復で総コスト{result['best_cost']:.2f}を達成"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"定期発注最適化エラー: {str(e)}"
            }

    elif function_name == "visualize_periodic_optimization":
        try:
            opt_result = arguments["optimization_result"]

            if opt_result.get("status") != "success":
                return {
                    "status": "error",
                    "message": "最適化結果が成功状態ではありません"
                }

            history = opt_result["optimization_history"]

            # コスト推移のグラフ
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=history["iteration"],
                y=history["cost"],
                mode='lines+markers',
                name='総コスト',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))

            fig.update_layout(
                title='定期発注最適化: コスト推移',
                xaxis_title='反復回数',
                yaxis_title='総コスト',
                template='plotly_white',
                hovermode='x unified',
                height=400
            )

            # グラフを保存
            viz_id = str(uuid.uuid4())
            output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
            os.makedirs(output_dir, exist_ok=True)

            file_path = os.path.join(output_dir, f"{viz_id}.html")
            pio.write_html(fig, file_path)

            # 勾配ノルム推移のグラフ
            fig2 = go.Figure()

            fig2.add_trace(go.Scatter(
                x=history["iteration"],
                y=history["gradient_norm"],
                mode='lines+markers',
                name='勾配ノルム',
                line=dict(color='#ff7f0e', width=2),
                marker=dict(size=6)
            ))

            fig2.update_layout(
                title='定期発注最適化: 勾配ノルム推移',
                xaxis_title='反復回数',
                yaxis_title='勾配ノルム',
                yaxis_type='log',
                template='plotly_white',
                hovermode='x unified',
                height=400
            )

            viz_id2 = str(uuid.uuid4())
            file_path2 = os.path.join(output_dir, f"{viz_id2}.html")
            pio.write_html(fig2, file_path2)

            return {
                "status": "success",
                "visualization_type": "定期発注最適化グラフ",
                "cost_chart_id": viz_id,
                "gradient_chart_id": viz_id2,
                "summary": {
                    "initial_cost": float(history["cost"][0]),
                    "final_cost": float(history["cost"][-1]),
                    "cost_reduction": float(history["cost"][0] - history["cost"][-1]),
                    "iterations": len(history["iteration"]),
                    "converged": opt_result["converged"]
                },
                "message": "定期発注最適化の結果を可視化しました"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"定期発注最適化可視化エラー: {str(e)}"
            }

    elif function_name == "visualize_safety_stock_network":
        try:
            opt_result = arguments["optimization_result"]

            if opt_result.get("status") != "success":
                return {
                    "status": "error",
                    "message": "最適化結果が成功状態ではありません"
                }

            # 可視化データの準備
            viz_data = prepare_network_visualization_data(opt_result)

            # ネットワーク図の生成
            fig = visualize_safety_stock_network(
                G=viz_data["G"],
                pos=viz_data["pos"],
                NRT=viz_data["NRT"],
                MaxLI=viz_data["MaxLI"],
                MinLT=viz_data["MinLT"],
                stage_names=viz_data["stage_names"]
            )

            # グラフを保存
            viz_id = str(uuid.uuid4())
            output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
            os.makedirs(output_dir, exist_ok=True)

            file_path = os.path.join(output_dir, f"{viz_id}.html")
            pio.write_html(fig, file_path)

            return {
                "status": "success",
                "visualization_type": "安全在庫配置ネットワーク図",
                "visualization_id": viz_id,
                "network_summary": {
                    "num_stages": len(viz_data["stage_names"]),
                    "num_connections": viz_data["G"].number_of_edges(),
                    "total_safety_stock": float(np.sum(viz_data["MaxLI"])),
                    "avg_lead_time": float(np.mean(viz_data["MinLT"]))
                },
                "message": "安全在庫配置ネットワークを可視化しました"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"ネットワーク可視化エラー: {str(e)}"
            }

    elif function_name == "calculate_eoq_incremental_discount":
        try:
            # 入力データの検証
            unit_costs = arguments["unit_costs"]
            quantity_breaks = arguments["quantity_breaks"]

            # リストの長さを確認
            if len(unit_costs) != len(quantity_breaks):
                return {
                    "status": "error",
                    "message": f"増分数量割引EOQ計算エラー: unit_costs（{len(unit_costs)}個）とquantity_breaks（{len(quantity_breaks)}個）の長さが一致しません。各価格帯に対して1つの最小発注量を指定してください。"
                }

            result = calculate_eoq_with_incremental_discount(
                K=arguments["K"],
                d=arguments["d"],
                h=arguments["h"],
                b=arguments["b"],
                r=arguments["r"],
                unit_costs=unit_costs,
                quantity_breaks=quantity_breaks
            )
            return {
                "status": "success",
                **result
            }
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"増分数量割引EOQ計算エラー: {str(e)}",
                "debug_info": {
                    "unit_costs": arguments.get("unit_costs"),
                    "quantity_breaks": arguments.get("quantity_breaks"),
                    "traceback": traceback.format_exc()
                }
            }

    elif function_name == "calculate_eoq_all_units_discount":
        try:
            # 入力データの検証
            unit_costs = arguments["unit_costs"]
            quantity_breaks = arguments["quantity_breaks"]

            # リストの長さを確認
            if len(unit_costs) != len(quantity_breaks):
                return {
                    "status": "error",
                    "message": f"全単位数量割引EOQ計算エラー: unit_costs（{len(unit_costs)}個）とquantity_breaks（{len(quantity_breaks)}個）の長さが一致しません。各価格帯に対して1つの最小発注量を指定してください。"
                }

            result = calculate_eoq_with_all_units_discount(
                K=arguments["K"],
                d=arguments["d"],
                h=arguments["h"],
                b=arguments["b"],
                r=arguments["r"],
                unit_costs=unit_costs,
                quantity_breaks=quantity_breaks
            )
            return {
                "status": "success",
                **result
            }
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"全単位数量割引EOQ計算エラー: {str(e)}",
                "debug_info": {
                    "unit_costs": arguments.get("unit_costs"),
                    "quantity_breaks": arguments.get("quantity_breaks"),
                    "traceback": traceback.format_exc()
                }
            }

    elif function_name == "visualize_eoq":
        try:
            fig = visualize_eoq_analysis(
                K=arguments["K"],
                d=arguments["d"],
                h=arguments["h"],
                b=arguments.get("b")
            )

            # グラフを保存
            viz_id = str(uuid.uuid4())
            output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
            os.makedirs(output_dir, exist_ok=True)

            file_path = os.path.join(output_dir, f"{viz_id}.html")
            pio.write_html(fig, file_path)

            # ユーザーキャッシュに保存
            if user_id is not None:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = pio.to_html(fig, include_plotlyjs='cdn')

            # 基本EOQ結果も計算
            eoq_result = calc_eoq_basic(
                K=arguments["K"],
                d=arguments["d"],
                h=arguments["h"],
                b=arguments.get("b")
            )

            return {
                "status": "success",
                "visualization_type": "EOQ分析グラフ",
                "visualization_id": viz_id,
                "optimal_order_quantity": eoq_result["optimal_order_quantity"],
                "message": "EOQ分析を可視化しました"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"EOQ可視化エラー: {str(e)}"
            }

    elif function_name == "find_optimal_learning_rate_periodic":
        try:
            # JSONデータのパース
            items_data = json.loads(arguments["items_data"])
            bom_data = json.loads(arguments["bom_data"])

            # カラム名を標準形式に変換
            for item in items_data:
                if 'avg_demand' in item and 'average_demand' not in item:
                    item['average_demand'] = item.pop('avg_demand')
                if 'demand_std' in item and 'sigma' not in item:
                    item['sigma'] = item.pop('demand_std')
                if 'holding_cost' in item and 'h' not in item:
                    item['h'] = item.pop('holding_cost')
                if 'stockout_cost' in item and 'b' not in item:
                    item['b'] = item.pop('stockout_cost')
                # デフォルト値の設定
                if 'capacity' not in item:
                    item['capacity'] = 10000
                if 'net_replenishment_time' not in item:
                    item['net_replenishment_time'] = item.get('process_time', 1)

            # BOMデータのカラム名を標準形式に変換とデフォルト値設定
            for bom in bom_data:
                # 'quantity' を 'units' に変換
                if 'quantity' in bom and 'units' not in bom:
                    bom['units'] = bom.pop('quantity')
                # デフォルト値の設定
                if 'units' not in bom:
                    bom['units'] = 1
                if 'allocation' not in bom:
                    bom['allocation'] = 1.0

            # DataFrameに変換
            network_data = {
                "stages": items_data,
                "connections": bom_data
            }
            stage_df, bom_df = prepare_stage_bom_data(network_data)

            # 学習率探索
            lr_result = find_optimal_learning_rate(
                stage_df,
                bom_df,
                max_iter=arguments.get("max_iter", 50),
                n_samples=10,
                n_periods=100,
                max_lr=arguments.get("max_lr", 10.0)
            )

            # 可視化
            fig = visualize_lr_search(lr_result)
            viz_id = str(uuid.uuid4())
            output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{viz_id}.html")
            pio.write_html(fig, file_path)

            # ユーザーキャッシュに保存
            if user_id is not None:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = pio.to_html(fig, include_plotlyjs='cdn')

            # Inf/NaNチェック
            best_cost = lr_result['best_cost']
            if np.isinf(best_cost) or np.isnan(best_cost):
                return {
                    "status": "error",
                    "message": f"最適学習率の探索が完了しましたが、最良コストは無限大（Infinity）となりました。\n\n推奨学習率: {lr_result['optimal_lr']:.2e}\n\nなお、最適化プロセスは指定された条件のもとで完了しましたが、コストが無限大となっていることに留意してください。\n\n訓練過程の可視化グラフが生成されました。可視化が完了しました。上に表示されたリンクをクリックして確認してください。",
                    "optimal_learning_rate": float(lr_result['optimal_lr']),
                    "best_cost": "infinity",
                    "visualization_id": viz_id
                }

            return {
                "status": "success",
                "optimal_learning_rate": float(lr_result['optimal_lr']),
                "best_cost": float(best_cost),
                "num_iterations": len(lr_result['lr_list']),
                "visualization_id": viz_id,
                "message": f"最適学習率を検出しました: {lr_result['optimal_lr']:.2e}"
            }
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"学習率探索エラー: {str(e)}",
                "traceback": traceback.format_exc()
            }

    elif function_name == "optimize_periodic_with_one_cycle":
        try:
            # JSONデータのパース
            items_data = json.loads(arguments["items_data"])
            bom_data = json.loads(arguments["bom_data"])

            # カラム名を標準形式に変換
            for item in items_data:
                if 'avg_demand' in item and 'average_demand' not in item:
                    item['average_demand'] = item.pop('avg_demand')
                if 'demand_std' in item and 'sigma' not in item:
                    item['sigma'] = item.pop('demand_std')
                if 'holding_cost' in item and 'h' not in item:
                    item['h'] = item.pop('holding_cost')
                if 'stockout_cost' in item and 'b' not in item:
                    item['b'] = item.pop('stockout_cost')
                # デフォルト値の設定
                if 'capacity' not in item:
                    item['capacity'] = 10000
                if 'net_replenishment_time' not in item:
                    item['net_replenishment_time'] = item.get('process_time', 1)

            # BOMデータのカラム名を標準形式に変換とデフォルト値設定
            for bom in bom_data:
                # 'quantity' を 'units' に変換
                if 'quantity' in bom and 'units' not in bom:
                    bom['units'] = bom.pop('quantity')
                # デフォルト値の設定
                if 'units' not in bom:
                    bom['units'] = 1
                if 'allocation' not in bom:
                    bom['allocation'] = 1.0

            # DataFrameに変換
            network_data = {
                "stages": items_data,
                "connections": bom_data
            }
            stage_df, bom_df = prepare_stage_bom_data(network_data)

            # Fit One Cycle最適化
            result = optimize_with_one_cycle(
                stage_df,
                bom_df,
                max_iter=arguments.get("max_iter", 200),
                n_samples=10,
                n_periods=100,
                max_lr=arguments.get("max_lr", 1.0)
            )

            # 訓練過程の可視化
            fig = visualize_training_progress(result)
            viz_id = str(uuid.uuid4())
            output_dir = os.environ.get("VISUALIZATION_OUTPUT_DIR", "/tmp/visualizations")
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{viz_id}.html")
            pio.write_html(fig, file_path)

            # ユーザーキャッシュに保存
            if user_id is not None:
                if user_id not in _optimization_cache:
                    _optimization_cache[user_id] = {}
                _optimization_cache[user_id][viz_id] = pio.to_html(fig, include_plotlyjs='cdn')

            # NaN/Infチェック
            if np.isinf(result['best_cost']):
                stage_results = []
                for idx, row in result['stage_df'].iterrows():
                    stage_results.append({
                        "name": row.get('name', f"Stage {idx}"),
                        "S": float(row['S']) if not np.isnan(row['S']) else 'NaN',
                        "local_S": float(row['local_base_stock_level']) if not np.isnan(row['local_base_stock_level']) else 'NaN'
                    })

                # デバッグ情報の収集
                debug_info = {
                    "stage_df_input": stage_df.to_dict(orient='records'),
                    "bom_df_input": bom_df.to_dict(orient='records'),
                    "stage_results": stage_results,
                    "num_iterations": len(result['cost_list']),
                    "cost_history": result['cost_list'][:10]  # 最初の10個
                }

                return {
                    "status": "error",
                    "message": f"Fit One Cycle最適化が完了しましたが、最良コストは無限大 (inf) となりました。\n\n【原因の可能性】\n1. 容量制約が厳しすぎる（デフォルト10000個）\n2. 需要が大きすぎて在庫が追いつかない\n3. サプライチェーンの構造に問題がある\n\n【計算結果】\n基在庫レベル:\n" + "\n".join([f"- {s['name']}: {s['S']}個" for s in stage_results]),
                    "best_cost": "inf",
                    "debug_info": debug_info
                }

            return {
                "status": "success",
                "best_cost": float(result['best_cost']),
                "num_iterations": len(result['cost_list']),
                "base_stock_levels": result['stage_df']['S'].tolist(),
                "local_base_stock_levels": result['stage_df']['local_base_stock_level'].tolist(),
                "stage_df": result['stage_df'].to_dict(orient='records'),
                "visualization_id": viz_id,
                "message": f"Fit One Cycle最適化が完了しました。最良コスト: {result['best_cost']:.2f}"
            }
        except Exception as e:
            import traceback
            return {
                "status": "error",
                "message": f"Fit One Cycle最適化エラー: {str(e)}",
                "traceback": traceback.format_exc()
            }

    else:
        return {
            "status": "error",
            "message": f"Unknown function: {function_name}"
        }
