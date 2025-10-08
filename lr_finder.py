"""
Phase 10: 学習率探索付き定期発注最適化 (Learning Rate Finder with Fit One Cycle)

機能:
- 学習率範囲探索（LR Range Test）
- Fit One Cycleスケジューラによる最適化
- 学習率・モメンタムスケジュールの可視化
- 最適化過程の詳細可視化
"""

import numpy as np
import pandas as pd
import networkx as nx
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from scmopt2.core import SCMGraph
from scmopt2.optinv import network_base_stock_simulation, initial_base_stock_level


def find_optimal_learning_rate(
    stage_df,
    bom_df,
    max_iter=100,
    n_samples=10,
    n_periods=100,
    seed=1,
    max_lr=10.0,
    moms=(0.85, 0.95)
):
    """
    学習率範囲探索（LR Range Test）

    学習率を指数的に増加させながら損失を記録し、最適な学習率を見つける

    Parameters
    ----------
    stage_df : pd.DataFrame
        ステージ情報
    bom_df : pd.DataFrame
        BOM情報
    max_iter : int
        最大反復回数
    n_samples : int
        シミュレーションのサンプル数
    n_periods : int
        シミュレーション期間
    seed : int
        乱数シード
    max_lr : float
        探索する最大学習率
    moms : tuple
        モメンタム範囲 (min, max)

    Returns
    -------
    dict : {
        'lr_list': 学習率の履歴,
        'cost_list': コストの履歴,
        'optimal_lr': 推奨学習率,
        'stage_df': 更新されたステージ情報,
        'best_cost': 最良コスト
    }
    """
    # グラフ構築
    G = SCMGraph()
    n = len(stage_df)
    h = np.zeros(n)
    b = np.zeros(n)
    capacity = np.zeros(n)
    mu = np.zeros(n)
    sigma = np.zeros(n)
    z = np.zeros(n)
    LT = np.zeros(n, dtype=int)

    # ノードを追加（データフレームのインデックスを使用）
    for idx, row in enumerate(stage_df.itertuples()):
        G.add_node(idx)  # 直接整数インデックスを使用
        mu[idx] = row.average_demand
        sigma[idx] = row.sigma
        h[idx] = row.h
        b[idx] = row.b
        z[idx] = row.z
        capacity[idx] = row.capacity
        LT[idx] = int(row.net_replenishment_time) + 1

    # BOMのエッジを追加（名前を整数インデックスにマッピング）
    name_to_idx = {row.name: idx for idx, row in enumerate(stage_df.itertuples())}
    for row in bom_df.itertuples():
        child_idx = name_to_idx.get(row.child, row.child)
        parent_idx = name_to_idx.get(row.parent, row.parent)
        G.add_edge(child_idx, parent_idx, weight=(row.units, row.allocation))
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

    # 初期化
    ELT, S = initial_base_stock_level(G, LT, mu, z, sigma)

    # Adam パラメータ
    step_size = 1e-10  # 非常に小さい学習率から開始
    beta_1 = moms[1]  # モメンタムは高めに固定
    beta_2 = 0.999
    epsilon = 1e-8
    m_t = np.zeros(n)
    v_t = np.zeros(n)

    lr_list = []
    cost_list = []
    best_cost = np.inf
    best_S = S.copy()
    prev_cost = np.inf

    for t in range(max_iter):
        # シミュレーション実行
        dC, cost, I = network_base_stock_simulation(
            G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
        )

        if cost < best_cost:
            best_cost = cost
            best_S = S.copy()

        lr_list.append(step_size)
        cost_list.append(cost)

        # 損失が増加し始めたら探索終了
        if cost > prev_cost and t > 5:
            break
        prev_cost = cost

        g_t = dC  # 勾配

        # Adam更新
        m_t = beta_1 * m_t + (1 - beta_1) * g_t
        v_t = beta_2 * v_t + (1 - beta_2) * (g_t ** 2)
        m_cap = m_t / (1 - beta_1 ** (t + 1))
        v_cap = v_t / (1 - beta_2 ** (t + 1))
        S = S - (step_size * m_cap) / (np.sqrt(v_cap) + epsilon)

        # 学習率を指数的に増加
        step_size *= 2.0
        if step_size > max_lr:
            break

    # 最適学習率の推定（コストが最小になる学習率）
    min_cost_idx = np.argmin(cost_list)
    optimal_lr = lr_list[min_cost_idx]

    # ローカル基在庫レベルの計算
    stage_df = stage_df.copy()
    stage_df["S"] = best_S
    local_S = np.zeros(n)
    for i in G:
        local_S[i] = best_S[i]
        for j in G.successors(i):
            local_S[i] -= best_S[j]
    stage_df["local_base_stock_level"] = local_S

    return {
        'lr_list': lr_list,
        'cost_list': cost_list,
        'optimal_lr': optimal_lr,
        'stage_df': stage_df,
        'best_cost': best_cost,
        'min_cost_idx': min_cost_idx
    }


def optimize_with_one_cycle(
    stage_df,
    bom_df,
    max_iter=200,
    n_samples=10,
    n_periods=100,
    seed=1,
    max_lr=1.0,
    moms=(0.85, 0.95)
):
    """
    Fit One Cycleスケジューラを使用した定期発注最適化

    学習率とモメンタムをコサイン関数でスケジュールし、高速収束を実現

    Parameters
    ----------
    stage_df : pd.DataFrame
        ステージ情報
    bom_df : pd.DataFrame
        BOM情報
    max_iter : int
        最大反復回数
    n_samples : int
        シミュレーションのサンプル数
    n_periods : int
        シミュレーション期間
    seed : int
        乱数シード
    max_lr : float
        最大学習率
    moms : tuple
        モメンタム範囲 (min, max)

    Returns
    -------
    dict : {
        'best_cost': 最良コスト,
        'stage_df': 更新されたステージ情報,
        'best_I': 最良在庫レベル,
        'cost_list': コストの履歴,
        'lr_schedule': 学習率スケジュール,
        'mom_schedule': モメンタムスケジュール
    }
    """
    # Fit One Cycle スケジュールの作成
    half_iter = max_iter // 2
    lrs = (max_lr / 25., max_lr)

    # 学習率: 低→高→低（コサインアニーリング）
    lr_schedule = np.concatenate([
        np.linspace(lrs[0], lrs[1], half_iter),
        lrs[1] / 2 + (lrs[1] / 2) * np.cos(np.linspace(0, np.pi, half_iter))
    ])

    # モメンタム: 高→低→高（学習率と逆相関）
    mom_schedule = np.concatenate([
        np.linspace(moms[1], moms[0], half_iter),
        moms[1] - (moms[1] - moms[0]) / 2 - (moms[1] - moms[0]) / 2 * np.cos(np.linspace(0, np.pi, half_iter))
    ])

    # グラフ構築
    G = SCMGraph()
    n = len(stage_df)
    h = np.zeros(n)
    b = np.zeros(n)
    capacity = np.zeros(n)
    mu = np.zeros(n)
    sigma = np.zeros(n)
    z = np.zeros(n)
    LT = np.zeros(n, dtype=int)

    # ノードを追加（データフレームのインデックスを使用）
    for idx, row in enumerate(stage_df.itertuples()):
        G.add_node(idx)  # 直接整数インデックスを使用
        mu[idx] = row.average_demand
        sigma[idx] = row.sigma
        h[idx] = row.h
        b[idx] = row.b
        z[idx] = row.z
        capacity[idx] = row.capacity
        LT[idx] = int(row.net_replenishment_time) + 1

    # BOMのエッジを追加（名前を整数インデックスにマッピング）
    name_to_idx = {row.name: idx for idx, row in enumerate(stage_df.itertuples())}
    for row in bom_df.itertuples():
        child_idx = name_to_idx.get(row.child, row.child)
        parent_idx = name_to_idx.get(row.parent, row.parent)
        G.add_edge(child_idx, parent_idx, weight=(row.units, row.allocation))
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

    # 初期化
    ELT, S = initial_base_stock_level(G, LT, mu, z, sigma)

    # デバッグ: 初期値の確認
    if np.any(np.isnan(S)) or np.any(np.isinf(S)):
        print(f"WARNING: Initial S contains NaN or Inf:")
        print(f"  mu: {mu}")
        print(f"  sigma: {sigma}")
        print(f"  z: {z}")
        print(f"  ELT: {ELT}")
        print(f"  S: {S}")

    # Adam パラメータ
    beta_2 = 0.999
    epsilon = 1e-8
    m_t = np.zeros(n)
    v_t = np.zeros(n)
    convergence = 1e-1

    cost_list = []
    best_cost = np.inf
    best_S = S.copy()
    best_I = None

    for t in range(max_iter):
        # シミュレーション実行
        dC, cost, I = network_base_stock_simulation(
            G, n_samples, n_periods, demand, capacity, LT, ELT, b, h, S, phi, alpha
        )

        if cost < best_cost:
            best_cost = cost
            best_S = S.copy()
            best_I = I.copy()

        cost_list.append(cost)
        g_t = dC  # 勾配

        # 収束判定
        norm = np.dot(g_t, g_t)
        if norm <= convergence:
            print(f"Converged at iteration {t}")
            break

        # スケジュールから学習率とモメンタムを取得
        step_size = lr_schedule[t]
        beta_1 = mom_schedule[t]

        # Adam更新
        m_t = beta_1 * m_t + (1 - beta_1) * g_t
        v_t = beta_2 * v_t + (1 - beta_2) * (g_t ** 2)
        m_cap = m_t / (1 - beta_1 ** (t + 1))
        v_cap = v_t / (1 - beta_2 ** (t + 1))
        S = S - (step_size * m_cap) / (np.sqrt(v_cap) + epsilon)

    # ローカル基在庫レベルの計算
    stage_df = stage_df.copy()
    stage_df["S"] = best_S
    local_S = np.zeros(n)
    for i in G:
        local_S[i] = best_S[i]
        for j in G.successors(i):
            local_S[i] -= best_S[j]
    stage_df["local_base_stock_level"] = local_S

    return {
        'best_cost': best_cost,
        'stage_df': stage_df,
        'best_I': best_I,
        'cost_list': cost_list,
        'lr_schedule': lr_schedule[:len(cost_list)],
        'mom_schedule': mom_schedule[:len(cost_list)]
    }


def visualize_lr_search(lr_result):
    """
    学習率探索結果の可視化

    Parameters
    ----------
    lr_result : dict
        find_optimal_learning_rate()の返り値

    Returns
    -------
    plotly.graph_objs.Figure
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=lr_result['lr_list'],
        y=lr_result['cost_list'],
        mode='markers+lines',
        name='Cost',
        marker=dict(size=8, color='red'),
        line=dict(color='red', width=2)
    ))

    # 最適学習率の位置を示す
    fig.add_vline(
        x=lr_result['optimal_lr'],
        line_dash="dash",
        line_color="green",
        annotation_text=f"Optimal LR={lr_result['optimal_lr']:.2e}",
        annotation_position="top"
    )

    fig.update_xaxes(type="log", title="Learning Rate (log scale)")
    fig.update_yaxes(title="Cost")
    fig.update_layout(
        title="Learning Rate Finder",
        hovermode='x unified',
        height=500
    )

    return fig


def visualize_training_progress(one_cycle_result):
    """
    Fit One Cycle訓練過程の可視化

    学習率・モメンタムスケジュールとコスト推移を表示

    Parameters
    ----------
    one_cycle_result : dict
        optimize_with_one_cycle()の返り値

    Returns
    -------
    plotly.graph_objs.Figure
    """
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Cost', 'Learning Rate Schedule', 'Momentum Schedule'),
        vertical_spacing=0.1
    )

    iterations = list(range(len(one_cycle_result['cost_list'])))

    # Cost
    fig.add_trace(
        go.Scatter(
            x=iterations,
            y=one_cycle_result['cost_list'],
            mode='lines',
            name='Cost',
            line=dict(color='blue', width=2)
        ),
        row=1, col=1
    )

    # Learning Rate
    fig.add_trace(
        go.Scatter(
            x=iterations,
            y=one_cycle_result['lr_schedule'],
            mode='lines',
            name='Learning Rate',
            line=dict(color='red', width=2)
        ),
        row=2, col=1
    )

    # Momentum
    fig.add_trace(
        go.Scatter(
            x=iterations,
            y=one_cycle_result['mom_schedule'],
            mode='lines',
            name='Momentum',
            line=dict(color='green', width=2)
        ),
        row=3, col=1
    )

    fig.update_xaxes(title_text="Iteration", row=3, col=1)
    fig.update_yaxes(title_text="Cost", row=1, col=1)
    fig.update_yaxes(title_text="LR", row=2, col=1)
    fig.update_yaxes(title_text="Momentum", row=3, col=1)

    fig.update_layout(
        title="Fit One Cycle Training Progress",
        height=900,
        showlegend=False
    )

    return fig


if __name__ == "__main__":
    # テスト用のサンプルデータ
    print("=== Learning Rate Finder Test ===")

    # サンプルデータの作成
    stage_df = pd.DataFrame({
        'name': ['サプライヤー', '工場', '製品'],
        'average_demand': [0, 0, 100],
        'sigma': [0, 0, 20],
        'h': [1, 2, 5],
        'b': [10, 20, 100],
        'z': [1.65, 1.65, 1.65],
        'capacity': [1000, 1000, 1000],
        'net_replenishment_time': [1, 1, 1],
        'x': [0, 1, 2],
        'y': [0, 0, 0]
    })

    bom_df = pd.DataFrame({
        'child': ['サプライヤー', '工場'],
        'parent': ['工場', '製品'],
        'units': [1, 1],
        'allocation': [1.0, 1.0]
    })

    # 学習率探索
    print("\n1. Running LR Finder...")
    lr_result = find_optimal_learning_rate(
        stage_df, bom_df,
        max_iter=50,
        n_samples=5,
        n_periods=50,
        max_lr=10.0
    )
    print(f"Optimal LR: {lr_result['optimal_lr']:.2e}")
    print(f"Best Cost: {lr_result['best_cost']:.2f}")

    # Fit One Cycle最適化
    print("\n2. Running Fit One Cycle...")
    result = optimize_with_one_cycle(
        stage_df, bom_df,
        max_iter=100,
        n_samples=5,
        n_periods=50,
        max_lr=lr_result['optimal_lr']
    )
    print(f"Final Cost: {result['best_cost']:.2f}")

    # 可視化
    fig1 = visualize_lr_search(lr_result)
    fig1.write_html("/tmp/lr_finder.html")
    print("\nLR Finder visualization saved to /tmp/lr_finder.html")

    fig2 = visualize_training_progress(result)
    fig2.write_html("/tmp/one_cycle_progress.html")
    print("Training progress visualization saved to /tmp/one_cycle_progress.html")
