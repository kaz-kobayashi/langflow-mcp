"""
Phase 12-1: ネットワークベースストックシミュレーション機能のテスト
"""
import sys
sys.path.append('.')

import numpy as np
import networkx as nx
from scmopt2.core import SCMGraph
from scmopt2.optinv import network_base_stock_simulation


def test_basic_3stage_network():
    """
    基本的な3段階ネットワークシミュレーション
    """
    print("=" * 60)
    print("Test 1: 基本的な3段階ネットワークシミュレーション")
    print("=" * 60)

    # 3段階サプライチェーン（線形）
    G = SCMGraph()
    G.add_nodes_from([0, 1, 2])
    G.add_edges_from([(0, 1), (1, 2)])

    n_samples = 10
    n_periods = 50
    n_stages = 3

    # 需要（最終段階のみ）
    demand = {}
    demand[0] = np.zeros((n_samples, n_periods))
    demand[1] = np.zeros((n_samples, n_periods))
    demand[2] = np.random.normal(100, 10, (n_samples, n_periods))

    # パラメータ
    capacity = np.array([1e6, 1e6, 1e6])
    LT = np.array([2, 2, 1])
    ELT = np.array([5, 3, 1])
    b = np.array([50, 100, 150])
    h = np.array([1, 2, 5])
    S = np.array([500, 400, 300])

    # BOM行列
    phi = np.array([
        [0, 1, 0],
        [0, 0, 1],
        [0, 0, 0]
    ])

    # 配分率行列
    alpha = np.ones((n_stages, n_stages))

    # シミュレーション実行
    dC, total_cost, I = network_base_stock_simulation(
        G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
    )

    print(f"総コスト: {total_cost:.2f}")
    print(f"勾配: {dC}")
    print(f"在庫データ形状: {I.shape}")

    # 各段階の在庫統計
    for stage in range(n_stages):
        stage_inv = I[:, stage, :]
        print(f"\n段階{stage}:")
        print(f"  平均在庫: {stage_inv.mean():.2f}")
        print(f"  標準偏差: {stage_inv.std():.2f}")
        print(f"  最小在庫: {stage_inv.min():.2f}")
        print(f"  最大在庫: {stage_inv.max():.2f}")
        print(f"  品切れ回数: {(stage_inv < 0).sum()}")

    assert total_cost > 0, "総コストが正の値ではありません"
    assert I.shape == (n_samples, n_stages, n_periods + 1), "在庫データの形状が不正です"
    assert len(dC) == n_stages, "勾配の長さが段階数と一致しません"

    print("\n✓ テスト合格\n")


def test_branching_network():
    """
    分岐構造を持つネットワークシミュレーション
    """
    print("=" * 60)
    print("Test 2: 分岐構造ネットワークシミュレーション")
    print("=" * 60)

    # 4段階サプライチェーン（分岐あり）
    #     0
    #    / \
    #   1   2
    #    \ /
    #     3
    G = SCMGraph()
    G.add_nodes_from([0, 1, 2, 3])
    G.add_edges_from([(0, 1), (0, 2), (1, 3), (2, 3)])

    n_samples = 10
    n_periods = 50
    n_stages = 4

    # 需要（最終段階のみ）
    demand = {}
    demand[0] = np.zeros((n_samples, n_periods))
    demand[1] = np.zeros((n_samples, n_periods))
    demand[2] = np.zeros((n_samples, n_periods))
    demand[3] = np.random.normal(150, 20, (n_samples, n_periods))

    # パラメータ
    capacity = np.array([1e6, 1e6, 1e6, 1e6])
    LT = np.array([3, 2, 2, 1])
    ELT = np.array([6, 3, 3, 1])
    b = np.array([30, 60, 60, 120])
    h = np.array([0.5, 1, 1, 3])
    S = np.array([600, 400, 400, 350])

    # BOM行列
    phi = np.array([
        [0, 1, 1, 0],
        [0, 0, 0, 0.5],
        [0, 0, 0, 0.5],
        [0, 0, 0, 0]
    ])

    # 配分率行列
    alpha = np.ones((n_stages, n_stages))

    # シミュレーション実行
    dC, total_cost, I = network_base_stock_simulation(
        G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
    )

    print(f"総コスト: {total_cost:.2f}")
    print(f"勾配: {dC}")

    # 各段階の在庫統計
    for stage in range(n_stages):
        stage_inv = I[:, stage, :]
        print(f"\n段階{stage}:")
        print(f"  平均在庫: {stage_inv.mean():.2f}")
        print(f"  品切れ回数: {(stage_inv < 0).sum()}")

    assert total_cost > 0, "総コストが正の値ではありません"
    assert I.shape == (n_samples, n_stages, n_periods + 1), "在庫データの形状が不正です"

    print("\n✓ テスト合格\n")


def test_varying_demand():
    """
    異なる需要パターンでのテスト
    """
    print("=" * 60)
    print("Test 3: 異なる需要パターン")
    print("=" * 60)

    G = SCMGraph()
    G.add_nodes_from([0, 1, 2])
    G.add_edges_from([(0, 1), (1, 2)])

    n_samples = 10
    n_periods = 50
    n_stages = 3

    demand_scenarios = [
        {"mu": 50, "sigma": 5, "name": "低需要・低変動"},
        {"mu": 100, "sigma": 10, "name": "中需要・中変動"},
        {"mu": 200, "sigma": 30, "name": "高需要・高変動"}
    ]

    for scenario in demand_scenarios:
        # 需要
        demand = {}
        demand[0] = np.zeros((n_samples, n_periods))
        demand[1] = np.zeros((n_samples, n_periods))
        demand[2] = np.random.normal(scenario["mu"], scenario["sigma"], (n_samples, n_periods))

        # パラメータ
        capacity = np.array([1e6, 1e6, 1e6])
        LT = np.array([2, 2, 1])
        ELT = np.array([5, 3, 1])
        b = np.array([50, 100, 150])
        h = np.array([1, 2, 5])
        S = np.array([scenario["mu"] * 5, scenario["mu"] * 4, scenario["mu"] * 3])

        phi = np.array([
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 0]
        ])
        alpha = np.ones((n_stages, n_stages))

        # シミュレーション実行
        dC, total_cost, I = network_base_stock_simulation(
            G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
        )

        print(f"\n{scenario['name']}:")
        print(f"  総コスト: {total_cost:.2f}")
        print(f"  平均在庫（段階2）: {I[:, 2, :].mean():.2f}")

    print("\n✓ テスト合格\n")


def test_capacity_constraints():
    """
    生産能力制約ありのテスト
    """
    print("=" * 60)
    print("Test 4: 生産能力制約")
    print("=" * 60)

    G = SCMGraph()
    G.add_nodes_from([0, 1, 2])
    G.add_edges_from([(0, 1), (1, 2)])

    n_samples = 10
    n_periods = 50
    n_stages = 3

    # 需要
    demand = {}
    demand[0] = np.zeros((n_samples, n_periods))
    demand[1] = np.zeros((n_samples, n_periods))
    demand[2] = np.random.normal(100, 10, (n_samples, n_periods))

    # パラメータ（生産能力に制約あり）
    capacity = np.array([150, 120, 110])  # 制約あり
    LT = np.array([2, 2, 1])
    ELT = np.array([5, 3, 1])
    b = np.array([50, 100, 150])
    h = np.array([1, 2, 5])
    S = np.array([500, 400, 300])

    phi = np.array([
        [0, 1, 0],
        [0, 0, 1],
        [0, 0, 0]
    ])
    alpha = np.ones((n_stages, n_stages))

    # シミュレーション実行
    dC, total_cost, I = network_base_stock_simulation(
        G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
    )

    print(f"総コスト: {total_cost:.2f}")
    print(f"勾配: {dC}")

    # 各段階の在庫統計
    for stage in range(n_stages):
        stage_inv = I[:, stage, :]
        print(f"\n段階{stage} (能力={capacity[stage]}):")
        print(f"  平均在庫: {stage_inv.mean():.2f}")
        print(f"  品切れ回数: {(stage_inv < 0).sum()}")

    assert total_cost > 0, "総コストが正の値ではありません"
    print("\n✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 12-1: ネットワークベースストックシミュレーション機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_basic_3stage_network()
        test_branching_network()
        test_varying_demand()
        test_capacity_constraints()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
