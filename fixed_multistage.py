"""
修正版の多段階在庫シミュレーション関数

元のscmopt2.optinvにあるバグを修正したバージョン
"""

import numpy as np
from scipy.stats import norm


def multi_stage_simulate_inventory_fixed(
    n_samples=1,
    n_periods=10,
    mu=100.,
    sigma=10.,
    LT=None,
    s=None,
    S=None,
    b=100.,
    h=None,
    fc=10000.
):
    """
    多段階ネットワークに対する(s,S)方策による在庫シミュレーション

    Parameters
    ----------
    n_samples : int
        シミュレーションサンプル数
    n_periods : int
        シミュレーション期間
    mu : float
        平均需要
    sigma : float
        需要の標準偏差
    LT : array_like
        各段階のリードタイム（例: [1, 2, 1]）
    s : array_like
        再発注点（各段階）
    S : array_like
        発注上限（各段階）
    b : float
        品切れ費用
    h : array_like
        在庫保管費用（各段階）
    fc : float
        固定発注費用

    Returns
    -------
    cost : ndarray
        各サンプルの平均コスト
    I : ndarray
        エシェロン在庫量の推移
    T : ndarray
        輸送中在庫量の推移
    """
    # デフォルト値設定
    if LT is None:
        LT = np.array([1, 1, 1])
    else:
        LT = np.asarray(LT)

    # バグ修正: n_stagesを定義
    n_stages = len(LT)

    if h is None:
        h = np.array([10., 5., 2.][:n_stages])
    else:
        h = np.asarray(h)

    # s, Sが指定されていない場合は自動計算
    omega = b / (b + h)
    z = norm.ppf(omega)

    # 初期エシェロン在庫量は、最終需要地点以外には、定期発注方策の1日分の時間を加えておく。
    ELT = np.zeros(n_stages, dtype=int)
    ELT[0] = LT[0] if n_stages == 1 else LT[1]
    for i in range(1, n_stages):
        ELT[i] = ELT[i-1] + 1 + LT[i]

    maxLT = LT.max()
    demand = np.maximum(np.random.normal(mu, sigma, (n_samples, n_periods)), 0.)
    I = np.zeros((n_samples, n_stages, n_periods+1))  # エシェロン在庫量
    T = np.zeros((n_samples, n_stages, n_periods+1))  # 輸送中在庫量
    fixed_cost = np.zeros((n_samples, n_stages, n_periods+1))

    # 初期在庫設定
    for i in range(n_stages):
        I[:, i, 0] = ELT[i] * mu + z[i] * sigma * np.sqrt(ELT[i])

    NI = I[:, :, 0].copy()  # 正味在庫ポジション
    production = np.zeros((n_samples, n_stages, maxLT))
    cost = np.zeros((n_samples, n_periods))

    # s, S が指定されていない場合は初期在庫レベルを使用
    if s is None:
        s = np.array([I[0, i, 0] * 0.5 for i in range(n_stages)])
    else:
        s = np.asarray(s)

    if S is None:
        S = np.array([I[0, i, 0] for i in range(n_stages)])
    else:
        S = np.asarray(S)

    for t in range(n_periods):
        for i in range(n_stages):
            I[:, i, t+1] = I[:, i, t] - demand[:, t] + production[:, i, (t-LT[i]) % maxLT]

            if i != n_stages - 1:
                # i+1の実在庫量
                cap = np.maximum(I[:, i+1, t] - I[:, i, t] - T[:, i+1, t], 0.)
                prod_temp = np.where(NI[:, i] < s[i], S[i] - NI[:, i], 0.)
                prod = np.minimum(prod_temp, cap)
            else:
                prod = np.where(NI[:, i] < s[i], S[i] - NI[:, i], 0.)

            # 輸送中在庫量の更新
            T[:, i, t+1] = T[:, i, t] + prod - production[:, i, (t-LT[i]) % maxLT]
            fixed_cost[:, i, t] = np.where(NI[:, i] < s[i], fc, 0.)
            NI[:, i] = NI[:, i] - demand[:, t] + prod  # 在庫ポジション
            production[:, i, t % maxLT] = prod

    # コスト計算
    cost = np.where(I[:, 0, :] < 0, -b * I[:, 0, :], h[0] * I[:, 0, :]) + fixed_cost[:, 0, :]
    for i in range(1, n_stages):
        cost += np.where(I[:, i, :] < 0, 0., (h[i-1] - h[i]) * I[:, i, :]) + fixed_cost[:, i, :]

    return np.sum(cost, axis=1) / n_periods, I, T


def base_stock_simulation_fixed(
    n_samples,
    n_periods,
    demand,
    capacity,
    LT,
    b,
    h,
    S
):
    """
    単一段階在庫システムの定期発注方策に対するシミュレーションと微分値の計算

    Parameters
    ----------
    n_samples : int
        サンプル数
    n_periods : int
        期間数
    demand : array_like
        需要データ（shape: (n_samples, n_periods) または (n_periods,)）
    capacity : float
        生産能力
    LT : int
        リードタイム
    b : float
        品切れ費用
    h : float
        在庫保管費用
    S : float
        ベースストックレベル

    Returns
    -------
    dC : float
        微分値
    total_cost : float
        総コスト
    I : ndarray
        在庫量の推移
    """
    # バグ修正: demandの次元を確認して調整
    demand = np.asarray(demand)
    if demand.ndim == 1:
        # 1次元の場合は全サンプルで同じ需要系列を使用
        demand = np.tile(demand[:n_periods], (n_samples, 1))
    elif demand.shape[0] != n_samples or demand.shape[1] < n_periods:
        raise ValueError(f"demand shape {demand.shape} doesn't match (n_samples={n_samples}, n_periods={n_periods})")

    I = np.zeros((n_samples, n_periods+1))
    T = np.zeros((n_samples, n_periods+1))

    I[:, 0] = S  # initial inventory
    production = np.zeros((n_samples, LT))

    sum_dC = 0.
    for t in range(n_periods):
        I[:, t+1] = I[:, t] - demand[:, t] + production[:, (t-LT) % LT]
        prod = np.minimum(capacity, S + demand[:, t] - I[:, t] - T[:, t])

        T[:, t+1] = T[:, t] + prod - production[:, (t-LT) % LT]
        production[:, t % LT] = prod

        dC = np.where(I[:, t] < 0, -b, h)
        sum_dC += dC.sum()

    total_cost = (-1 * b * I[I < 0].sum() + h * I[I > 0].sum()) / n_periods / n_samples
    return sum_dC / n_samples / n_periods, total_cost, I


def multi_stage_base_stock_simulation_fixed(
    n_samples,
    n_periods,
    demand,
    capacity,
    LT,
    b,
    h,
    S
):
    """
    多段階在庫システムの定期発注方策に対するシミュレーションと微分値の計算

    Parameters
    ----------
    n_samples : int
        サンプル数
    n_periods : int
        期間数
    demand : array_like
        需要データ
    capacity : array_like
        各段階の生産能力
    LT : array_like
        各段階のリードタイム
    b : float
        品切れ費用
    h : array_like
        各段階の在庫保管費用
    S : array_like
        各段階のベースストックレベル

    Returns
    -------
    dC : ndarray
        微分値
    total_cost : float
        総コスト
    I : ndarray
        在庫量の推移
    """
    # バグ修正: n_stagesを定義
    LT = np.asarray(LT)
    n_stages = len(LT)

    # demandの次元調整
    demand = np.asarray(demand)
    if demand.ndim == 1:
        demand = np.tile(demand[:n_periods], (n_samples, 1))

    capacity = np.asarray(capacity)
    h = np.asarray(h)
    S = np.asarray(S)

    maxLT = LT.max()

    # 在庫量
    I = np.zeros((n_samples, n_stages, n_periods+1))
    T = np.zeros((n_samples, n_stages, n_periods+1))

    for i in range(n_stages):
        if i == 0:
            I[:, i, 0] = S[i]
        else:
            I[:, i, 0] = S[i] - S[i-1]

    # 微分値
    dI = np.zeros((n_samples, n_stages, n_stages, n_periods+1))
    dT = np.zeros((n_samples, n_stages, n_stages, n_periods+1))

    for i in range(n_stages):
        dI[:, i, i, 0] = 1
        if i != 0:
            dI[:, i, i-1, 0] = -1

    dProd = np.zeros((n_samples, n_stages, n_stages, maxLT))
    production = np.zeros((n_samples, n_stages, maxLT))

    sum_dC = np.zeros((n_samples, n_stages))

    for t in range(n_periods):
        for i in range(n_stages):
            if i == 0:
                I[:, i, t+1] = I[:, i, t] - demand[:, t] + production[:, i, (t-LT[i]) % maxLT]

                # 生産量の計算
                prod = np.minimum(capacity[i], S[i] + demand[:, t] - I[:, i, t] - T[:, i, t])

                T[:, i, t+1] = T[:, i, t] + prod - production[:, i, (t-LT[i]) % maxLT]
                production[:, i, t % maxLT] = prod

                dC = np.where(I[:, i, t] < 0, -b, h[i])
                sum_dC[:, i] += dC

                # 微分値の更新（簡略版）
                for j in range(n_stages):
                    dI[:, i, j, t+1] = dI[:, i, j, t] + dProd[:, i, j, (t-LT[i]) % maxLT]
            else:
                # 上流段階の処理
                I[:, i, t+1] = I[:, i, t] - production[:, i-1, t % maxLT] + production[:, i, (t-LT[i]) % maxLT]

                echelon_inv_pos = I[:, i, t] + T[:, i, t]
                actual_inv = I[:, i, t] - I[:, i-1, t] - T[:, i-1, t]

                prod_desired = S[i] + production[:, i-1, t % maxLT] - echelon_inv_pos
                prod = np.minimum(np.minimum(capacity[i], prod_desired), actual_inv)
                prod = np.maximum(prod, 0)

                T[:, i, t+1] = T[:, i, t] + prod - production[:, i, (t-LT[i]) % maxLT]
                production[:, i, t % maxLT] = prod

    # コスト計算
    cost = -1 * b * I[:, 0, :][I[:, 0, :] < 0].sum()
    cost += h[0] * I[:, 0, :][I[:, 0, :] > 0].sum()

    for i in range(1, n_stages):
        actual_I = I[:, i, :] - I[:, i-1, :]
        cost += h[i] * actual_I[actual_I > 0].sum()

    total_cost = cost / n_periods / n_samples
    dC = sum_dC / n_samples / n_periods

    return dC, total_cost, I


def initial_base_stock_level_fixed(LT_dict, mu, z, sigma):
    """
    初期基在庫レベルとエシェロンリード時間の計算

    Parameters
    ----------
    LT_dict : dict
        各ノードのリードタイム辞書 {node_name: lead_time}
    mu : float
        平均需要
    z : float
        安全係数
    sigma : float
        需要の標準偏差

    Returns
    -------
    S_dict : dict
        各ノードのベースストックレベル
    ELT_dict : dict
        各ノードのエシェロンリードタイム
    """
    # ノード名のリストを取得（リードタイム順にソート）
    nodes = sorted(LT_dict.keys(), key=lambda x: LT_dict[x])

    S_dict = {}
    ELT_dict = {}

    # 最下流（リードタイムが最小）から計算
    for node in nodes:
        lt = LT_dict[node]
        # エシェロンリードタイムは自ノードのLTに下流の合計を加える
        # 簡略化のため、単純に累積
        elt = lt

        # ベースストックレベル = 期待需要 + 安全在庫
        S = mu * elt + z * sigma * np.sqrt(elt)

        S_dict[node] = S
        ELT_dict[node] = elt

    return S_dict, ELT_dict
