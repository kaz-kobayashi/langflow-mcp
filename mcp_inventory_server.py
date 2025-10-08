"""
MCP Server for Supply Chain Inventory Optimization
サプライチェーン在庫最適化のためのMCPサーバー
"""

from fastmcp import FastMCP
import sys
sys.path.append('.')

from scmopt2.optinv import (
    make_excel_messa,
    prepare_df_for_messa,
    prepare_opt_for_messa,
    messa_for_excel,
    solve_SSA,
    extract_data_for_SSA,
    make_df_for_SSA,
    approximate_ss,
    eoq,
    fit_demand
)
from eoq_calculator import (
    calculate_eoq as calc_eoq_basic,
    calculate_eoq_with_incremental_discount,
    calculate_eoq_with_all_units_discount,
    visualize_eoq_analysis,
    visualize_eoq_with_discount
)
import pandas as pd
import json
from openpyxl import load_workbook, Workbook
import tempfile
import os

# MCPサーバーの初期化
mcp = FastMCP("Supply Chain Inventory Optimizer")

@mcp.tool()
def calculate_eoq(
    K: float,
    d: float,
    h: float,
    b: float = None
) -> dict:
    """
    基本的な経済発注量（EOQ）を計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）- Noneの場合はバックオーダーなし

    Returns:
        dict: EOQ計算結果（最適発注量など）
    """
    return calc_eoq_basic(K=K, d=d, h=h, b=b)


@mcp.tool()
def calculate_eoq_incremental_discount(
    K: float,
    d: float,
    h: float,
    b: float,
    r: float,
    unit_costs: list,
    quantity_breaks: list
) -> dict:
    """
    増分数量割引対応のEOQを計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        r: 割引率
        unit_costs: 各価格帯の単価リスト [c0, c1, c2, ...]
        quantity_breaks: 各価格帯の最小発注量 [θ0, θ1, θ2, ...]

    Returns:
        dict: EOQ計算結果（最適発注量、総コスト、選択された価格帯など）
    """
    return calculate_eoq_with_incremental_discount(
        K=K, d=d, h=h, b=b, r=r,
        unit_costs=unit_costs, quantity_breaks=quantity_breaks
    )


@mcp.tool()
def calculate_eoq_all_units_discount(
    K: float,
    d: float,
    h: float,
    b: float,
    r: float,
    unit_costs: list,
    quantity_breaks: list
) -> dict:
    """
    全単位数量割引対応のEOQを計算

    Args:
        K: 発注固定費用（円/回）
        d: 平均需要量（units/日）
        h: 在庫保管費用（円/unit/日）
        b: 品切れ費用（円/unit/日）
        r: 割引率
        unit_costs: 各価格帯の単価リスト [c0, c1, c2, ...]
        quantity_breaks: 各価格帯の最小発注量 [θ0, θ1, θ2, ...]

    Returns:
        dict: EOQ計算結果（最適発注量、総コスト、選択された価格帯など）
    """
    return calculate_eoq_with_all_units_discount(
        K=K, d=d, h=h, b=b, r=r,
        unit_costs=unit_costs, quantity_breaks=quantity_breaks
    )


@mcp.tool()
def calculate_safety_stock(
    mu: float,
    sigma: float,
    LT: int,
    b: float,
    h: float,
    fc: float = 10000.0
) -> dict:
    """
    安全在庫レベルを計算

    Args:
        mu: 平均需要量（units/日）
        sigma: 需要の標準偏差
        LT: リードタイム（日）
        b: 品切れ費用（円/unit/日）
        h: 在庫保管費用（円/unit/日）
        fc: 発注固定費用（円/回、デフォルト10000）

    Returns:
        dict: 安全在庫レベルと関連情報
    """
    result = approximate_ss(mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc)

    return {
        "safety_stock_level": float(result["S"]),
        "service_level": float(result["P"]),
        "expected_cost": float(result["C"]),
        "parameters": {
            "average_demand": mu,
            "demand_std_dev": sigma,
            "lead_time": LT,
            "stockout_cost": b,
            "holding_cost": h,
            "fixed_order_cost": fc
        }
    }


@mcp.tool()
def optimize_safety_stock_allocation(
    items_data: str,
    bom_data: str
) -> dict:
    """
    マルチエシュロン在庫ネットワークの安全在庫配置を最適化（MESSA）

    Args:
        items_data: 品目データのJSON文字列
            例: '[{"name":"A","process_time":1,"max_service_time":3,"avg_demand":100,"demand_std":10,"holding_cost":1,"stockout_cost":100,"fixed_cost":1000}]'
        bom_data: BOM（部品表）データのJSON文字列
            例: '[{"child":"B","parent":"A","quantity":1}]'

    Returns:
        dict: 最適化結果（各拠点の安全在庫レベル、リードタイムなど）
    """
    # JSONパース
    items = json.loads(items_data)
    bom = json.loads(bom_data)

    # 一時Excelファイル作成
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


@mcp.tool()
def analyze_inventory_network(
    items_data: str,
    bom_data: str
) -> dict:
    """
    在庫ネットワークを分析し、ネットワーク構造とコスト情報を返す

    Args:
        items_data: 品目データのJSON文字列
        bom_data: BOMデータのJSON文字列

    Returns:
        dict: ネットワーク分析結果（ノード数、エッジ数、コスト構造など）
    """
    # JSONパース
    items = json.loads(items_data)
    bom = json.loads(bom_data)

    # 一時Excelファイル作成
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
                "is_dag": True  # MESSAは常にDAG
            },
            "nodes": nodes_info,
            "edges": edges_info
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # MCPサーバー起動
    mcp.run()
