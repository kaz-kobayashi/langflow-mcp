"""
Phase 8 & Phase 11-1: Supply Chain Network Visualization
サプライチェーンネットワーク可視化機能

- Phase 8: 安全在庫配置ネットワークの可視化
- Phase 11-1: 汎用的なサプライチェーンネットワーク可視化
"""
import numpy as np
import plotly.graph_objects as go
import networkx as nx
import pandas as pd


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
                title=dict(text='保証リードタイム<br>(MinLT)', side='right'),
                xanchor='left'
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


# ========================================
# Phase 11-1: 汎用的なネットワーク可視化
# ========================================

def visualize_supply_chain_network(
    items_data: list,
    bom_data: list,
    optimization_result: dict = None,
    layout: str = "hierarchical"
) -> go.Figure:
    """
    サプライチェーンネットワークをPlotlyで可視化

    Parameters
    ----------
    items_data : list
        品目データのリスト
        例: [{"name": "製品A", "h": 5, "b": 100, ...}, ...]
    bom_data : list
        BOM（部品展開表）データのリスト
        例: [{"child": "部品B", "parent": "製品A", "units": 1}, ...]
    optimization_result : dict, optional
        最適化結果（オプション）
        例: {"best_NRT": [...], "best_MaxLI": [...], "best_MinLT": [...]}
    layout : str
        レイアウトタイプ
        - "hierarchical": 階層レイアウト（デフォルト）
        - "spring": バネモデルレイアウト
        - "circular": 円形レイアウト

    Returns
    -------
    plotly.graph_objects.Figure
        ネットワーク可視化グラフ
    """
    # NetworkXグラフを構築
    G = nx.DiGraph()

    # ノード（品目）を追加
    item_dict = {}
    for idx, item in enumerate(items_data):
        name = item.get("name", f"Item_{idx}")
        G.add_node(name, **item)
        item_dict[name] = item

    # エッジ（BOM関係）を追加
    for bom in bom_data:
        child = bom.get("child")
        parent = bom.get("parent")
        units = bom.get("units", 1)
        allocation = bom.get("allocation", 1.0)

        if child and parent:
            G.add_edge(child, parent, units=units, allocation=allocation)

    # レイアウトを計算
    if layout == "hierarchical":
        # 階層的レイアウト（多段階サプライチェーンに適している）
        pos = _hierarchical_layout(G)
    elif layout == "spring":
        pos = nx.spring_layout(G, k=2, iterations=50)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    else:
        pos = nx.spring_layout(G)

    # エッジのトレースを作成
    edge_trace = _create_edge_trace(G, pos, bom_data)

    # ノードのトレースを作成
    node_trace = _create_node_trace(G, pos, item_dict, optimization_result)

    # グラフを作成
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="サプライチェーンネットワーク",
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            height=600
        )
    )

    return fig


def _hierarchical_layout(G: nx.DiGraph) -> dict:
    """
    階層的レイアウトを計算

    Parameters
    ----------
    G : networkx.DiGraph
        NetworkXのグラフ

    Returns
    -------
    dict
        {node: (x, y)} の位置辞書
    """
    # トポロジカルソートで階層を決定
    try:
        layers = list(nx.topological_generations(G))
    except:
        # DAGでない場合はデフォルトレイアウト
        return nx.spring_layout(G)

    pos = {}
    max_layer_size = max(len(layer) for layer in layers)

    for level, layer in enumerate(layers):
        # この階層のノード数
        layer_size = len(layer)
        # 階層内でのノード間隔を均等に
        y_positions = np.linspace(-1, 1, layer_size) if layer_size > 1 else [0]

        for idx, node in enumerate(layer):
            # x座標は階層レベル、y座標は階層内の位置
            pos[node] = (level, y_positions[idx])

    return pos


def _create_edge_trace(G: nx.DiGraph, pos: dict, bom_data: list) -> go.Scatter:
    """
    エッジのトレースを作成

    Parameters
    ----------
    G : networkx.DiGraph
        NetworkXのグラフ
    pos : dict
        ノードの位置辞書
    bom_data : list
        BOMデータ

    Returns
    -------
    plotly.graph_objects.Scatter
        エッジのトレース
    """
    edge_x = []
    edge_y = []
    edge_text = []

    bom_dict = {}
    for bom in bom_data:
        key = (bom.get("child"), bom.get("parent"))
        bom_dict[key] = bom

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]

        # エッジの線を描画
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        # エッジ情報を取得
        bom = bom_dict.get(edge, {})
        units = bom.get("units", 1)
        allocation = bom.get("allocation", 1.0)
        edge_text.append(f"使用量: {units}, 配分率: {allocation:.2f}")

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='text',
        text=edge_text,
        mode='lines'
    )

    return edge_trace


def _create_node_trace(
    G: nx.DiGraph,
    pos: dict,
    item_dict: dict,
    optimization_result: dict = None
) -> go.Scatter:
    """
    ノードのトレースを作成

    Parameters
    ----------
    G : networkx.DiGraph
        NetworkXのグラフ
    pos : dict
        ノードの位置辞書
    item_dict : dict
        品目データの辞書
    optimization_result : dict, optional
        最適化結果（オプション）

    Returns
    -------
    plotly.graph_objects.Scatter
        ノードのトレース
    """
    node_x = []
    node_y = []
    node_text = []
    node_color = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        # ノード情報を取得
        item = item_dict.get(node, {})
        h = item.get("h", item.get("holding_cost", "N/A"))
        b = item.get("b", item.get("stockout_cost", "N/A"))
        avg_demand = item.get("average_demand", item.get("avg_demand", 0))

        # ホバーテキストを作成
        hover_text = f"<b>{node}</b><br>"
        hover_text += f"在庫保管費用: {h}<br>"
        hover_text += f"品切れ費用: {b}<br>"
        hover_text += f"平均需要: {avg_demand}<br>"

        # 最適化結果がある場合、追加情報を表示
        if optimization_result:
            node_idx = list(G.nodes()).index(node)
            if "best_NRT" in optimization_result:
                nrt = optimization_result["best_NRT"][node_idx]
                hover_text += f"安全在庫: {nrt:.2f}<br>"
            if "best_MaxLI" in optimization_result:
                max_li = optimization_result["best_MaxLI"][node_idx]
                hover_text += f"最大LI: {max_li:.2f}<br>"
            if "best_MinLT" in optimization_result:
                min_lt = optimization_result["best_MinLT"][node_idx]
                hover_text += f"最小LT: {min_lt:.2f}<br>"

        node_text.append(hover_text)

        # ノードの色を決定（最適化結果がある場合）
        if optimization_result and "best_NRT" in optimization_result:
            node_idx = list(G.nodes()).index(node)
            nrt = optimization_result["best_NRT"][node_idx]
            # 安全在庫レベルに応じて色を変える
            node_color.append(nrt)
        else:
            # デフォルトの色
            node_color.append(avg_demand)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[item_dict.get(node, {}).get("name", node) for node in G.nodes()],
        textposition="top center",
        hovertext=node_text,
        marker=dict(
            showscale=True,
            colorscale='YlOrRd',
            reversescale=False,
            color=node_color,
            size=30,
            colorbar=dict(
                thickness=15,
                title=dict(text='在庫レベル' if optimization_result else '平均需要', side='right'),
                xanchor='left'
            ),
            line=dict(width=2, color='DarkSlateGrey')
        )
    )

    return node_trace
