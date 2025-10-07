"""
定期発注最適化（Adam最適化アルゴリズムによる基在庫レベル最適化）
"""
import numpy as np
import pandas as pd
import networkx as nx
from scmopt2.core import SCMGraph
from scmopt2.optinv import network_base_stock_simulation, initial_base_stock_level


def optimize_periodic_inventory(
    stage_df,
    bom_df,
    max_iter=100,
    n_samples=10,
    n_periods=100,
    seed=1,
    learning_rate=1.0,
    beta_1=0.9,
    beta_2=0.999,
    convergence_threshold=1e-5
):
    """
    定期発注方策の最適化（Adam最適化アルゴリズム）

    Parameters
    ----------
    stage_df : pd.DataFrame
        ステージ情報（name, average_demand, sigma, h, b, z, capacity, net_replenishment_time, x, y）
    bom_df : pd.DataFrame
        BOM情報（child, parent, units, allocation）
    max_iter : int
        最大反復回数
    n_samples : int
        シミュレーションのサンプル数
    n_periods : int
        シミュレーション期間
    seed : int
        乱数シード
    learning_rate : float
        学習率（α）
    beta_1 : float
        1次モーメント減衰率
    beta_2 : float
        2次モーメント減衰率
    convergence_threshold : float
        収束判定閾値

    Returns
    -------
    dict
        最適化結果（cost, stage_df, optimization_history）
    """
    # ネットワーク構築
    G = SCMGraph()
    n = len(stage_df)

    h = np.zeros(n)
    b = np.zeros(n)
    capacity = np.zeros(n)
    mu = np.zeros(n)
    sigma = np.zeros(n)
    z = np.zeros(n)
    LT = np.zeros(n, dtype=int)

    pos = {}
    for idx, row in enumerate(stage_df.itertuples()):
        G.add_node(row.name)
        mu[idx] = row.average_demand
        sigma[idx] = row.sigma
        h[idx] = row.h
        b[idx] = row.b
        z[idx] = row.z
        capacity[idx] = row.capacity
        pos[row.name] = (row.x, row.y)
        LT[idx] = int(row.net_replenishment_time) + 1

    for row in bom_df.itertuples():
        G.add_edge(row.child, row.parent, weight=(row.units, row.allocation))

    # ノードのラベル付け替え
    mapping = {i: idx for idx, i in enumerate(G)}
    G = nx.relabel_nodes(G, mapping=mapping, copy=True)

    phi, alpha = {}, {}
    for i, j in G.edges():
        phi[i, j] = G[i][j]["weight"][0]
        alpha[i, j] = G[i][j]["weight"][1]

    # 需要生成
    np.random.seed(seed)
    demand = {}
    for i in G:
        if G.out_degree(i) == 0:
            demand[i] = np.random.normal(mu[i], sigma[i], (n_samples, n_periods))
            demand[i] = np.maximum(demand[i], 0.)

    # 初期基在庫レベルの設定
    ELT, S = initial_base_stock_level(G, LT, mu, z, sigma)

    # Adam最適化の初期化
    epsilon = 1e-8
    m_t = np.zeros(n)
    v_t = np.zeros(n)

    best_cost = np.inf
    best_S = S.copy()
    best_I = None

    # 最適化履歴
    optimization_history = {
        "iteration": [],
        "cost": [],
        "gradient_norm": [],
        "base_stock_levels": []
    }

    # Adam最適化ループ
    for t in range(max_iter):
        # シミュレーション実行と勾配計算
        dC, cost, I = network_base_stock_simulation(
            G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
        )

        if cost < best_cost:
            best_cost = cost
            best_S = S.copy()
            best_I = I.copy()

        g_t = dC  # 勾配

        # 移動平均の更新
        m_t = beta_1 * m_t + (1 - beta_1) * g_t

        # 勾配の二乗の移動平均の更新
        v_t = beta_2 * v_t + (1 - beta_2) * (g_t ** 2)

        # バイアス補正
        m_cap = m_t / (1 - beta_1 ** (t + 1))
        v_cap = v_t / (1 - beta_2 ** (t + 1))

        # パラメータ更新
        S = S - (learning_rate * m_cap) / (np.sqrt(v_cap) + epsilon)

        # 勾配ノルムの計算
        gradient_norm = np.linalg.norm(g_t)

        # 履歴の記録
        optimization_history["iteration"].append(t)
        optimization_history["cost"].append(float(cost))
        optimization_history["gradient_norm"].append(float(gradient_norm))
        optimization_history["base_stock_levels"].append(S.copy().tolist())

        # 収束判定
        if gradient_norm <= convergence_threshold:
            break

    # 結果の整理
    result_stage_df = stage_df.copy()
    result_stage_df["base_stock_level"] = best_S

    # ローカル基在庫レベルの計算
    local_S = np.zeros(n)
    for i in G:
        local_S[i] = best_S[i]
        for j in G.successors(i):
            local_S[i] -= best_S[j]
    result_stage_df["local_base_stock_level"] = local_S

    return {
        "best_cost": float(best_cost),
        "stage_df": result_stage_df,
        "inventory_data": best_I,
        "optimization_history": optimization_history,
        "converged": gradient_norm <= convergence_threshold,
        "final_iteration": t,
        "echelon_lead_time": ELT.tolist()
    }


def prepare_stage_bom_data(network_data):
    """
    ネットワークデータからstage_dfとbom_dfを準備

    Parameters
    ----------
    network_data : dict
        ネットワーク定義

    Returns
    -------
    tuple
        (stage_df, bom_df)
    """
    stages = network_data.get("stages", [])
    connections = network_data.get("connections", [])

    stage_df = pd.DataFrame(stages)
    bom_df = pd.DataFrame(connections)

    # 必須カラムの確認
    required_stage_cols = [
        "name", "average_demand", "sigma", "h", "b", "z",
        "capacity", "net_replenishment_time", "x", "y"
    ]
    required_bom_cols = ["child", "parent", "units", "allocation"]

    for col in required_stage_cols:
        if col not in stage_df.columns:
            raise ValueError(f"stage_dfに必須カラム '{col}' がありません")

    for col in required_bom_cols:
        if col not in bom_df.columns:
            raise ValueError(f"bom_dfに必須カラム '{col}' がありません")

    return stage_df, bom_df
