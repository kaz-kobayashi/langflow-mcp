#!/usr/bin/env python
"""Test optimization function"""

import json
from scmopt2.optinv import (
    tabu_search_for_SSA,
    make_excel_messa,
    prepare_opt_for_messa
)

# サンプルデータ（simple pattern）
items = [
    {
        "name": "製品A",
        "process_time": 2,
        "max_service_time": 5,
        "avg_demand": 100,
        "demand_std": 20,
        "holding_cost": 5,
        "stockout_cost": 100,
        "fixed_cost": 10000
    },
    {
        "name": "部品B",
        "process_time": 1,
        "max_service_time": 3,
        "avg_demand": 200,
        "demand_std": 30,
        "holding_cost": 3,
        "stockout_cost": 80,
        "fixed_cost": 8000
    },
    {
        "name": "原材料C",
        "process_time": 1,
        "max_service_time": 2,
        "avg_demand": 300,
        "demand_std": 40,
        "holding_cost": 2,
        "stockout_cost": 50,
        "fixed_cost": 5000
    }
]

bom = [
    {"child": "部品B", "parent": "製品A", "quantity": 2},
    {"child": "原材料C", "parent": "部品B", "quantity": 1}
]

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

# 最適化実行
print("準備中...")
G, ProcTime, LTUB, z, mu, sigma, h = prepare_opt_for_messa(wb)

print(f"グラフノード数: {len(G.nodes())}")
print(f"ProcTime: {ProcTime}")
print(f"LTUB: {LTUB}")
print(f"z: {z}")
print(f"mu: {mu}")
print(f"sigma: {sigma}")
print(f"h: {h}")

print("\n最適化実行中...")
best_cost, best_sol, best_NRT, best_MaxLI, best_MinLT = tabu_search_for_SSA(
    G, ProcTime, LTUB, z, mu, sigma, h, max_iter=100
)

print(f"\n結果:")
print(f"best_cost: {best_cost}")
print(f"best_cost type: {type(best_cost)}")
print(f"best_sol: {best_sol}")
print(f"best_sol type: {type(best_sol)}")
print(f"best_NRT: {best_NRT}")
print(f"best_NRT type: {type(best_NRT)}")
print(f"best_MaxLI: {best_MaxLI}")
print(f"best_MinLT: {best_MinLT}")

print("\nノード毎の結果:")
for idx, node in enumerate(G.nodes()):
    print(f"ノード {idx} ({node}): NRT={best_NRT[idx]}, MaxLI={best_MaxLI[idx]}, MinLT={best_MinLT[idx]}")
