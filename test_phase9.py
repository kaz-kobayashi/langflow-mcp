"""
Phase 9: EOQ（経済発注量）計算機能のテスト
"""
import sys
sys.path.append('.')

from eoq_calculator import (
    calculate_eoq,
    calculate_eoq_with_incremental_discount,
    calculate_eoq_with_all_units_discount,
    compare_eoq_scenarios,
    visualize_eoq_analysis,
    visualize_eoq_with_discount
)


def test_basic_eoq():
    """
    基本EOQ計算のテスト
    """
    print("=" * 60)
    print("Test 1: 基本EOQ計算（バックオーダーなし）")
    print("=" * 60)

    result = calculate_eoq(K=100, d=10, h=1, b=None)

    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"パラメータ: {result['parameters']}")
    print(f"バックオーダー: {result['parameters']['backorder_allowed']}")

    assert result['optimal_order_quantity'] > 0, "発注量は正の値である必要があります"
    assert result['parameters']['backorder_allowed'] == False
    print("✓ テスト合格\n")


def test_eoq_with_backorder():
    """
    バックオーダー対応EOQのテスト
    """
    print("=" * 60)
    print("Test 2: バックオーダー対応EOQ計算")
    print("=" * 60)

    result = calculate_eoq(K=100, d=10, h=1, b=10)

    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"安全在庫係数の平方根: {result['optimal_reorder_point_or_safety_stock_sqrt']:.2f}")
    print(f"パラメータ: {result['parameters']}")

    assert result['optimal_order_quantity'] > 0
    assert result['parameters']['backorder_allowed'] == True
    assert result['parameters']['stockout_cost'] == 10
    print("✓ テスト合格\n")


def test_incremental_discount():
    """
    増分数量割引EOQのテスト
    """
    print("=" * 60)
    print("Test 3: 増分数量割引EOQ")
    print("=" * 60)

    result = calculate_eoq_with_incremental_discount(
        K=100,
        d=1000,
        h=2,
        b=100,
        r=0.1,
        unit_costs=[10, 9, 8],
        quantity_breaks=[0, 100, 200]
    )

    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"総コスト: {result['total_cost']:.2f}")
    print(f"選択された価格帯: {result['selected_price_tier']}")
    print(f"選択された単価: {result['selected_unit_cost']}")
    print(f"パラメータ: {result['parameters']}")

    assert result['optimal_order_quantity'] > 0
    assert result['total_cost'] > 0
    assert 0 <= result['selected_price_tier'] < len(result['parameters']['unit_costs'])
    print("✓ テスト合格\n")


def test_all_units_discount():
    """
    全単位数量割引EOQのテスト
    """
    print("=" * 60)
    print("Test 4: 全単位数量割引EOQ")
    print("=" * 60)

    result = calculate_eoq_with_all_units_discount(
        K=100,
        d=1000,
        h=2,
        b=100,
        r=0.1,
        unit_costs=[10, 9, 8],
        quantity_breaks=[0, 100, 200]
    )

    print(f"最適発注量: {result['optimal_order_quantity']:.2f}")
    print(f"総コスト: {result['total_cost']:.2f}")
    print(f"選択された価格帯: {result['selected_price_tier']}")
    print(f"選択された単価: {result['selected_unit_cost']}")
    print(f"パラメータ: {result['parameters']}")

    assert result['optimal_order_quantity'] > 0
    assert result['total_cost'] > 0
    assert 0 <= result['selected_price_tier'] < len(result['parameters']['unit_costs'])
    print("✓ テスト合格\n")


def test_compare_scenarios():
    """
    複数シナリオの比較テスト
    """
    print("=" * 60)
    print("Test 5: 複数EOQシナリオの比較")
    print("=" * 60)

    scenarios = [
        {
            'name': '基本EOQ',
            'type': 'basic',
            'params': {'K': 100, 'd': 10, 'h': 1, 'b': 10}
        },
        {
            'name': '増分割引',
            'type': 'incremental',
            'params': {
                'K': 100, 'd': 1000, 'h': 2, 'b': 100, 'r': 0.1,
                'unit_costs': [10, 9, 8],
                'quantity_breaks': [0, 100, 200]
            }
        },
        {
            'name': '全単位割引',
            'type': 'all_units',
            'params': {
                'K': 100, 'd': 1000, 'h': 2, 'b': 100, 'r': 0.1,
                'unit_costs': [10, 9, 8],
                'quantity_breaks': [0, 100, 200]
            }
        }
    ]

    result = compare_eoq_scenarios(scenarios)

    print(f"比較シナリオ数: {len(result['scenarios'])}")
    for scenario in result['scenarios']:
        print(f"\n{scenario['name']} ({scenario['type']}):")
        if 'total_cost' in scenario['result']:
            print(f"  総コスト: {scenario['result']['total_cost']:.2f}")
        print(f"  最適発注量: {scenario['result']['optimal_order_quantity']:.2f}")

    print(f"\n最良シナリオ（コスト基準）: {result['comparison_summary']['best_scenario_by_cost']}")

    assert len(result['scenarios']) == 3
    assert 'best_scenario_by_cost' in result['comparison_summary']
    print("\n✓ テスト合格\n")


def test_visualization():
    """
    可視化機能のテスト
    """
    print("=" * 60)
    print("Test 6: EOQ可視化")
    print("=" * 60)

    # 基本EOQの可視化
    fig = visualize_eoq_analysis(K=100, d=10, h=1, b=10)
    assert fig is not None
    print("基本EOQ可視化: ✓")

    # グラフをHTMLとして保存
    fig.write_html("/tmp/test_eoq_basic.html")
    print(f"グラフを保存: /tmp/test_eoq_basic.html")

    # 数量割引EOQの可視化
    fig2 = visualize_eoq_with_discount(
        K=100, d=1000, h=2, b=100, r=0.1,
        unit_costs=[10, 9, 8],
        quantity_breaks=[0, 100, 200],
        discount_type="all"
    )
    assert fig2 is not None
    print("数量割引EOQ可視化: ✓")

    fig2.write_html("/tmp/test_eoq_discount.html")
    print(f"グラフを保存: /tmp/test_eoq_discount.html")

    print("\n✓ テスト合格\n")


def test_realistic_scenario():
    """
    現実的なシナリオでのテスト
    """
    print("=" * 60)
    print("Test 7: 現実的なシナリオ")
    print("=" * 60)

    # 実際のビジネスケース: 電子部品の発注
    # - 発注固定費用: 5000円
    # - 日次需要: 50個
    # - 在庫保管費: 0.5円/個/日
    # - 品切れ費用: 20円/個/日

    result = calculate_eoq(K=5000, d=50, h=0.5, b=20)

    print("シナリオ: 電子部品の発注最適化")
    print(f"  発注固定費用: 5000円")
    print(f"  日次需要: 50個")
    print(f"  在庫保管費: 0.5円/個/日")
    print(f"  品切れ費用: 20円/個/日")
    print(f"\n最適発注量: {result['optimal_order_quantity']:.0f}個")
    print(f"発注頻度: 約{result['optimal_order_quantity']/50:.1f}日ごと")

    assert result['optimal_order_quantity'] > 0
    print("\n✓ テスト合格\n")


def test_discount_comparison():
    """
    増分割引と全単位割引の比較
    """
    print("=" * 60)
    print("Test 8: 増分割引 vs 全単位割引の比較")
    print("=" * 60)

    params = {
        'K': 100, 'd': 1000, 'h': 2, 'b': 100, 'r': 0.1,
        'unit_costs': [10, 9.5, 9, 8.5, 8],
        'quantity_breaks': [0, 50, 100, 150, 200]
    }

    incremental = calculate_eoq_with_incremental_discount(**params)
    all_units = calculate_eoq_with_all_units_discount(**params)

    print("増分数量割引:")
    print(f"  最適発注量: {incremental['optimal_order_quantity']:.2f}")
    print(f"  総コスト: {incremental['total_cost']:.2f}")
    print(f"  選択価格帯: {incremental['selected_price_tier']} (単価={incremental['selected_unit_cost']})")

    print("\n全単位数量割引:")
    print(f"  最適発注量: {all_units['optimal_order_quantity']:.2f}")
    print(f"  総コスト: {all_units['total_cost']:.2f}")
    print(f"  選択価格帯: {all_units['selected_price_tier']} (単価={all_units['selected_unit_cost']})")

    cost_diff = abs(incremental['total_cost'] - all_units['total_cost'])
    print(f"\nコスト差: {cost_diff:.2f}円/日")

    if incremental['total_cost'] < all_units['total_cost']:
        print("→ 増分割引の方が有利")
    elif all_units['total_cost'] < incremental['total_cost']:
        print("→ 全単位割引の方が有利")
    else:
        print("→ 同等")

    print("\n✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 9: EOQ計算機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_basic_eoq()
        test_eoq_with_backorder()
        test_incremental_discount()
        test_all_units_discount()
        test_compare_scenarios()
        test_visualization()
        test_realistic_scenario()
        test_discount_comparison()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
