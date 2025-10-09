"""
Phase 11-1: ネットワーク可視化機能のテスト
"""
import sys
sys.path.append('.')

from network_visualizer import visualize_supply_chain_network


def test_basic_network_visualization():
    """
    基本的なネットワーク可視化のテスト
    """
    print("=" * 60)
    print("Test 1: 基本的なネットワーク可視化")
    print("=" * 60)

    # 3段階サプライチェーン
    items_data = [
        {"name": "サプライヤーA", "h": 1, "b": 10, "average_demand": 0},
        {"name": "工場", "h": 2, "b": 20, "average_demand": 0},
        {"name": "製品", "h": 5, "b": 100, "average_demand": 100}
    ]

    bom_data = [
        {"child": "サプライヤーA", "parent": "工場", "units": 1, "allocation": 1.0},
        {"child": "工場", "parent": "製品", "units": 1, "allocation": 1.0}
    ]

    fig = visualize_supply_chain_network(items_data, bom_data, layout="hierarchical")
    
    assert fig is not None, "グラフが生成されませんでした"
    
    # HTMLとして保存
    fig.write_html("/tmp/test_network_basic.html")
    print(f"✓ 基本ネットワーク可視化を保存: /tmp/test_network_basic.html")
    print("✓ テスト合格\n")


def test_complex_network_visualization():
    """
    複雑なネットワーク可視化のテスト
    """
    print("=" * 60)
    print("Test 2: 複雑なネットワーク可視化（4段階）")
    print("=" * 60)

    # 4段階サプライチェーン
    items_data = [
        {"name": "原材料", "h": 0.5, "b": 5, "average_demand": 0},
        {"name": "部品A", "h": 1, "b": 10, "average_demand": 0},
        {"name": "部品B", "h": 1, "b": 10, "average_demand": 0},
        {"name": "組立", "h": 3, "b": 30, "average_demand": 0},
        {"name": "製品", "h": 5, "b": 100, "average_demand": 200}
    ]

    bom_data = [
        {"child": "原材料", "parent": "部品A", "units": 2, "allocation": 0.6},
        {"child": "原材料", "parent": "部品B", "units": 1, "allocation": 0.4},
        {"child": "部品A", "parent": "組立", "units": 1, "allocation": 1.0},
        {"child": "部品B", "parent": "組立", "units": 2, "allocation": 1.0},
        {"child": "組立", "parent": "製品", "units": 1, "allocation": 1.0}
    ]

    fig = visualize_supply_chain_network(items_data, bom_data, layout="hierarchical")
    
    assert fig is not None, "グラフが生成されませんでした"
    
    # HTMLとして保存
    fig.write_html("/tmp/test_network_complex.html")
    print(f"✓ 複雑なネットワーク可視化を保存: /tmp/test_network_complex.html")
    print("✓ テスト合格\n")


def test_network_with_optimization_result():
    """
    最適化結果を含むネットワーク可視化のテスト
    """
    print("=" * 60)
    print("Test 3: 最適化結果を含むネットワーク可視化")
    print("=" * 60)

    items_data = [
        {"name": "サプライヤー", "h": 1, "b": 10, "average_demand": 0},
        {"name": "工場", "h": 2, "b": 20, "average_demand": 0},
        {"name": "製品", "h": 5, "b": 100, "average_demand": 100}
    ]

    bom_data = [
        {"child": "サプライヤー", "parent": "工場", "units": 1, "allocation": 1.0},
        {"child": "工場", "parent": "製品", "units": 1, "allocation": 1.0}
    ]

    # ダミーの最適化結果
    optimization_result = {
        "best_NRT": [5.0, 10.0, 20.0],  # 安全在庫レベル
        "best_MaxLI": [3.0, 6.0, 12.0],  # 最大在庫インデックス
        "best_MinLT": [1.0, 2.0, 3.0]    # 最小リードタイム
    }

    fig = visualize_supply_chain_network(
        items_data, 
        bom_data, 
        optimization_result=optimization_result,
        layout="hierarchical"
    )
    
    assert fig is not None, "グラフが生成されませんでした"
    
    # HTMLとして保存
    fig.write_html("/tmp/test_network_with_opt.html")
    print(f"✓ 最適化結果付きネットワーク可視化を保存: /tmp/test_network_with_opt.html")
    print("✓ テスト合格\n")


def test_different_layouts():
    """
    異なるレイアウトのテスト
    """
    print("=" * 60)
    print("Test 4: 異なるレイアウトアルゴリズム")
    print("=" * 60)

    items_data = [
        {"name": "A", "h": 1, "b": 10, "average_demand": 0},
        {"name": "B", "h": 2, "b": 20, "average_demand": 0},
        {"name": "C", "h": 3, "b": 30, "average_demand": 0},
        {"name": "D", "h": 5, "b": 100, "average_demand": 50}
    ]

    bom_data = [
        {"child": "A", "parent": "B", "units": 1, "allocation": 1.0},
        {"child": "B", "parent": "D", "units": 1, "allocation": 1.0},
        {"child": "C", "parent": "D", "units": 1, "allocation": 1.0}
    ]

    layouts = ["hierarchical", "spring", "circular"]
    
    for layout in layouts:
        fig = visualize_supply_chain_network(items_data, bom_data, layout=layout)
        assert fig is not None, f"{layout}レイアウトのグラフが生成されませんでした"
        
        filename = f"/tmp/test_network_{layout}.html"
        fig.write_html(filename)
        print(f"✓ {layout}レイアウトを保存: {filename}")
    
    print("✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 11-1: ネットワーク可視化機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_basic_network_visualization()
        test_complex_network_visualization()
        test_network_with_optimization_result()
        test_different_layouts()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
