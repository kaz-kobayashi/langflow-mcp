"""
定期発注最適化の計算コストベンチマーク
"""
import time
import numpy as np
import pandas as pd
from scmopt2.optinv import network_base_stock_simulation, initial_base_stock_level
from scmopt2.core import SCMGraph
import networkx as nx

def benchmark_periodic_opt():
    """
    periodic_inv_optの計算時間を測定
    """
    # シンプルな2段階サプライチェーンのテスト
    stage_df = pd.DataFrame({
        'name': ['原材料', '製品'],
        'average_demand': [0, 100],
        'sigma': [0, 20],
        'h': [1, 2],
        'b': [10, 50],
        'z': [1.65, 1.65],
        'capacity': [1000, 1000],
        'net_replenishment_time': [2, 1],
        'x': [0, 1],
        'y': [0, 0]
    })

    bom_df = pd.DataFrame({
        'child': ['原材料'],
        'parent': ['製品'],
        'units': [1],
        'allocation': [1.0]
    })

    # ネットワーク構築（SCMGraphを使用）
    G = SCMGraph()
    n = len(stage_df)

    for idx, row in enumerate(stage_df.itertuples()):
        G.add_node(row.name)

    for row in bom_df.itertuples():
        G.add_edge(row.child, row.parent, weight=(row.units, row.allocation))

    mapping = {i: idx for idx, i in enumerate(G)}
    G = nx.relabel_nodes(G, mapping=mapping, copy=True)

    # phi, alpha の設定
    phi, alpha = {}, {}
    for i, j in G.edges():
        phi[i, j] = G[i][j]["weight"][0]
        alpha[i, j] = G[i][j]["weight"][1]

    # パラメータ設定
    mu = stage_df['average_demand'].values
    sigma = stage_df['sigma'].values
    LT = (stage_df['net_replenishment_time'].values + 1).astype(int)
    z = stage_df['z'].values

    # 異なるパラメータでベンチマーク
    test_cases = [
        {"n_samples": 10, "n_periods": 100, "max_iter": 1, "name": "小規模(デフォルト)"},
        {"n_samples": 100, "n_periods": 100, "max_iter": 1, "name": "中規模サンプル"},
        {"n_samples": 10, "n_periods": 1000, "max_iter": 1, "name": "長期間"},
        {"n_samples": 10, "n_periods": 100, "max_iter": 10, "name": "多反復"},
    ]

    print("=" * 60)
    print("定期発注最適化の計算時間ベンチマーク")
    print("=" * 60)

    for case in test_cases:
        np.random.seed(1)

        # 需要生成
        demand = {}
        for i in G:
            if G.out_degree(i) == 0:
                demand[i] = np.random.normal(mu[i], sigma[i], (case["n_samples"], case["n_periods"]))
                demand[i] = np.maximum(demand[i], 0.)

        ELT, S = initial_base_stock_level(G, LT, mu, z, sigma)

        # 計算時間測定
        start_time = time.time()

        for _ in range(case["max_iter"]):
            dC, cost, I = network_base_stock_simulation(
                G,
                case["n_samples"],
                case["n_periods"],
                demand,
                S,
                mu,
                sigma,
                stage_df['h'].values,
                stage_df['b'].values,
                LT,
                phi,
                alpha
            )

        elapsed = time.time() - start_time

        print(f"\n{case['name']}:")
        print(f"  設定: samples={case['n_samples']}, periods={case['n_periods']}, iter={case['max_iter']}")
        print(f"  計算時間: {elapsed:.3f}秒")
        print(f"  平均コスト: {cost:.2f}")

if __name__ == "__main__":
    benchmark_periodic_opt()
