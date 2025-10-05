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
    ww
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


def get_visualization_html(user_id: int) -> str:
    """ユーザーの可視化HTMLを取得"""
    if user_id not in _optimization_cache:
        raise KeyError(f"No cache found for user_id: {user_id}")

    cache = _optimization_cache[user_id]
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

            return {
                "status": "success",
                "optimization_results": result_data,
                "total_cost": float(best_sol.get("best_cost", 0))
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
            G = prepare_opt_for_messa(wb)

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

            # キャッシュにHTML保存（後でエンドポイントから取得）
            _optimization_cache[user_id]["visualization_html"] = html_content

            # 可視化用URLを生成
            viz_url = f"/api/visualization/{user_id}"

            return {
                "status": "success",
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
            mu = arguments["mu"]
            sigma = arguments["sigma"]
            LT = arguments["lead_time"]
            service_level = arguments["service_level"]
            h = arguments.get("holding_cost", None)

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

    else:
        return {
            "status": "error",
            "message": f"Unknown function: {function_name}"
        }
