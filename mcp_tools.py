"""
MCP Tools integration for OpenAI Function Calling
"""

import json
import sys
sys.path.append('.')

from scmopt2.optinv import (
    eoq,
    approximate_ss,
    solve_SSA,
    make_excel_messa,
    prepare_opt_for_messa,
    draw_graph_for_SSA
)
import plotly.io as pio
import os
import uuid
from datetime import datetime

# ユーザーごとの計算結果キャッシュ
# {user_id: {"G": graph, "pos": positions, "best_sol": solution, "items": items_data, "bom": bom_data}}
_optimization_cache = {}


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
            "name": "visualize_inventory_network",
            "description": "在庫ネットワークと最適化結果をグラフ・図として可視化します。安全在庫レベル、リードタイム、コストなどを視覚的に表示するインタラクティブなHTMLファイルを生成し、閲覧用のURLを返します。グラフや図、チャート、ネットワーク図が必要な時は必ずこのツールを使用してください。",
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
            "description": "直前に実行した安全在庫最適化(optimize_safety_stock_allocation)の結果を可視化します。ユーザーが「結果を可視化して」「グラフを見せて」「図を表示して」などと依頼した場合に使用します。データを再度指定する必要はありません。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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

    elif function_name == "calculate_safety_stock":
        result = approximate_ss(
            mu=arguments["mu"],
            sigma=arguments["sigma"],
            LT=arguments["LT"],
            b=arguments["b"],
            h=arguments["h"],
            fc=arguments.get("fc", 10000.0)
        )
        # approximate_ss関数はタプル (S, cost) を返す
        S, cost = result
        return {
            "safety_stock_level": float(S),
            "expected_cost": float(cost),
            "parameters": {
                "average_demand": arguments["mu"],
                "demand_std_dev": arguments["sigma"],
                "lead_time": arguments["LT"],
                "stockout_cost": arguments["b"],
                "holding_cost": arguments["h"],
                "fixed_order_cost": arguments.get("fc", 10000.0)
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
            G = prepare_opt_for_messa(wb)
            best_sol = solve_SSA(G)

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

    elif function_name == "visualize_inventory_network":
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

        try:
            # 最適化実行
            G = prepare_opt_for_messa(wb)
            best_sol = solve_SSA(G)

            # ネットワークポジション計算（G.layout()を使用）
            pos = G.layout()

            # 可視化
            fig = draw_graph_for_SSA(G, pos, best_sol["best_NRT"], best_sol["best_MaxLI"], best_sol["best_MinLT"])

            # HTMLファイルとして保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_id = str(uuid.uuid4())[:8]
            filename = f"network_{timestamp}_{file_id}.html"
            filepath = os.path.join("static", "visualizations", filename)

            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # HTML保存
            pio.write_html(fig, filepath)

            # URLを生成
            viz_url = f"/static/visualizations/{filename}"

            return {
                "status": "success",
                "visualization_url": viz_url,
                "filename": filename,
                "message": "可視化が完成しました。リンクをクリックして確認してください。"
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

            # HTMLファイルとして保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_id = str(uuid.uuid4())[:8]
            filename = f"network_{timestamp}_{file_id}.html"
            filepath = os.path.join("static", "visualizations", filename)

            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # HTML保存
            pio.write_html(fig, filepath)

            # URLを生成
            viz_url = f"/static/visualizations/{filename}"

            return {
                "status": "success",
                "visualization_url": viz_url,
                "filename": filename,
                "message": "可視化が完成しました。リンクをクリックして確認してください。",
                "total_cost": float(best_sol.get("best_cost", 0))
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
