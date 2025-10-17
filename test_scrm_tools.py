#!/usr/bin/env python3
"""SCRM Tools のテストスクリプト"""

import json
from mcp_tools import execute_mcp_function

print("=" * 80)
print("SCRM Tools テスト")
print("=" * 80)
print()

# Test 1: generate_scrm_data
print("【Test 1】 generate_scrm_data - ベンチマーク問題01からデータ生成")
print("-" * 80)
result1 = execute_mcp_function("generate_scrm_data", {
    "benchmark_id": "01",
    "n_plants": 3,
    "n_flex": 2,
    "seed": 1
})
print(json.dumps(result1, indent=2, ensure_ascii=False))
print()

# Test 2: save_scrm_data_to_csv
print("【Test 2】 save_scrm_data_to_csv - データをCSVに保存")
print("-" * 80)
result2 = execute_mcp_function("save_scrm_data_to_csv", {
    "benchmark_id": "01",
    "filename_suffix": "test_01",
    "n_plants": 3,
    "n_flex": 2,
    "seed": 1
})
print(json.dumps(result2, indent=2, ensure_ascii=False))
print()

# Test 3: load_scrm_data_from_csv
print("【Test 3】 load_scrm_data_from_csv - CSVからデータ読み込み")
print("-" * 80)
result3 = execute_mcp_function("load_scrm_data_from_csv", {
    "filename_suffix": "test_01"
})
print(json.dumps(result3, indent=2, ensure_ascii=False))
print()

# Test 4: visualize_scrm_graph (BOM)
print("【Test 4】 visualize_scrm_graph - BOMグラフ可視化")
print("-" * 80)
result4_bom = execute_mcp_function("visualize_scrm_graph", {
    "filename_suffix": "test_01",
    "graph_type": "bom",
    "title": "BOMグラフ（テスト）"
})
print(json.dumps(result4_bom, indent=2, ensure_ascii=False))
print()

# Test 5: visualize_scrm_graph (plant)
print("【Test 5】 visualize_scrm_graph - 工場ネットワークグラフ可視化")
print("-" * 80)
result4_plant = execute_mcp_function("visualize_scrm_graph", {
    "filename_suffix": "test_01",
    "graph_type": "plant",
    "title": "工場ネットワークグラフ（テスト）"
})
print(json.dumps(result4_plant, indent=2, ensure_ascii=False))
print()

# Test 6: visualize_scrm_graph (production)
print("【Test 6】 visualize_scrm_graph - 生産グラフ可視化")
print("-" * 80)
result4_prod = execute_mcp_function("visualize_scrm_graph", {
    "filename_suffix": "test_01",
    "graph_type": "production",
    "title": "生産グラフ（テスト）"
})
print(json.dumps(result4_prod, indent=2, ensure_ascii=False))
print()

# Test 7: analyze_supply_chain_risk
print("【Test 7】 analyze_supply_chain_risk - サプライチェーンリスク分析")
print("-" * 80)
result5 = execute_mcp_function("analyze_supply_chain_risk", {
    "filename_suffix": "test_01"
})
print(json.dumps(result5, indent=2, ensure_ascii=False))
print()

# Test 8: visualize_scrm_network
print("【Test 8】 visualize_scrm_network - リスクネットワーク可視化")
print("-" * 80)
result6 = execute_mcp_function("visualize_scrm_network", {
    "filename_suffix": "test_01"
})
print(json.dumps(result6, indent=2, ensure_ascii=False))
print()

print("=" * 80)
print("全てのSCRMツールのテストが完了しました！")
print("=" * 80)
