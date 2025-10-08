"""
安全在庫配置ネットワークの可視化
"""
import numpy as np
import plotly.graph_objects as go


def visualize_safety_stock_network(G, pos, NRT, MaxLI, MinLT, stage_names=None):
    """
    安全在庫配置問題の結果をPlotlyで描画する関数

    Parameters
    ----------
    G : networkx.DiGraph
        サプライチェーンネットワーク
    pos : dict
        ノード位置 {node_id: (x, y)}
    NRT : np.ndarray
        正味補充時間（Net Replenishment Time）
    MaxLI : np.ndarray
        最大在庫レベル
    MinLT : np.ndarray
        最小リードタイム（保証リードタイム）
    stage_names : list, optional
        ステージ名のリスト

    Returns
    -------
    plotly.graph_objects.Figure
        可視化されたネットワーク図
    """
    # ノードサイズの計算（NRTに基づく）
    max_nrt = max(NRT.max(), 1.0)
    size_ = NRT / max_nrt * 20.0 + 10.0

    # ノードの座標とテキスト
    x_, y_, text_ = [], [], []
    for idx, i in enumerate(G):
        x_.append(pos[i][0])
        y_.append(pos[i][1])

        # ノード名を取得
        if stage_names is not None and idx < len(stage_names):
            node_name = stage_names[idx]
        else:
            node_name = str(i)

        # ホバーテキスト
        hover_text = (
            f"<b>{node_name}</b><br>"
            f"NRT（正味補充時間）: {NRT[idx]:.2f}<br>"
            f"MaxLI（最大在庫）: {MaxLI[idx]:.2f}<br>"
            f"MinLT（保証リードタイム）: {MinLT[idx]:.2f}"
        )
        text_.append(hover_text)

    # ノードのトレース
    node_trace = go.Scatter(
        x=x_,
        y=y_,
        mode='markers',
        text=text_,
        hoverinfo="text",
        marker=dict(
            size=size_,
            colorscale="Greys",
            reversescale=True,
            color=MinLT,
            colorbar=dict(
                thickness=15,
                title='保証リードタイム<br>(MinLT)',
                xanchor='left',
                titleside='right'
            ),
            line=dict(width=2, color='#333')
        ),
        name="nodes",
        showlegend=False
    )

    # エッジの座標
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    # エッジのトレース
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines',
        name="edges",
        showlegend=False
    )

    # レイアウト
    layout = go.Layout(
        title="安全在庫配置ネットワーク<br><sub>ノードサイズ = NRT（正味補充時間）、色 = 保証リードタイム</sub>",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        hovermode='closest',
        plot_bgcolor='rgba(240,240,240,0.9)',
        height=600,
        margin=dict(l=20, r=20, t=80, b=20)
    )

    data = [edge_trace, node_trace]
    fig = go.Figure(data, layout)
    return fig


def prepare_network_visualization_data(optimization_result):
    """
    optimize_safety_stock_allocationの結果から可視化用データを準備

    Parameters
    ----------
    optimization_result : dict
        optimize_safety_stock_allocationの実行結果

    Returns
    -------
    dict
        可視化に必要なデータ
    """
    import networkx as nx

    if optimization_result.get("status") != "success":
        raise ValueError("最適化結果が成功状態ではありません")

    # items と bom から再構築
    items = optimization_result.get("items", [])
    bom = optimization_result.get("bom", [])
    pos_data = optimization_result.get("pos_data", {})
    optimization_results = optimization_result.get("optimization_results", [])

    # NetworkXグラフを構築
    G = nx.DiGraph()

    # ノードの追加
    pos = {}
    stage_names = []
    for idx, item in enumerate(items):
        G.add_node(idx)
        # pos_dataから座標を取得、なければitem内のx,y、それもなければデフォルト
        if str(idx) in pos_data:
            pos[idx] = tuple(pos_data[str(idx)])
        elif 'x' in item and 'y' in item:
            pos[idx] = (item['x'], item['y'])
        else:
            pos[idx] = (idx, 0)
        stage_names.append(item.get("name", f"Stage_{idx}"))

    # エッジの追加
    for b in bom:
        # child/parentの名前からインデックスを取得
        child_idx = next((i for i, item in enumerate(items) if item["name"] == b["child"]), None)
        parent_idx = next((i for i, item in enumerate(items) if item["name"] == b["parent"]), None)

        if child_idx is not None and parent_idx is not None:
            G.add_edge(child_idx, parent_idx)

    # 最適化結果から値を取得
    n = len(items)
    NRT = np.zeros(n)
    MaxLI = np.zeros(n)
    MinLT = np.zeros(n)

    for res in optimization_results:
        node_idx = res.get("node")
        if node_idx is not None and node_idx < n:
            NRT[node_idx] = res.get("safety_stock", 0)  # safety_stockがNRTに相当
            MaxLI[node_idx] = res.get("service_time", 0)  # service_timeがMaxLIに相当
            MinLT[node_idx] = res.get("lead_time", 0)  # lead_timeがMinLTに相当

    return {
        "G": G,
        "pos": pos,
        "NRT": NRT,
        "MaxLI": MaxLI,
        "MinLT": MinLT,
        "stage_names": stage_names
    }
