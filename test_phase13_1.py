"""
Phase 13-1: 動的計画法による安全在庫配置のテスト
"""
import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function

def test_basic_3stage_tree():
    """
    基本的な3段階ツリー構造での動的計画法テスト
    """
    print("=" * 70)
    print("Test 1: 基本的な3段階ツリー構造")
    print("=" * 70)

    items_data = [
        {
            "name": "原材料",
            "h": 1.0,
            "mu": 0,
            "sigma": 0,
            "proc_time": 1.0,
            "lead_time_lb": 2.0,
            "lead_time_ub": 4.0
        },
        {
            "name": "中間品",
            "h": 2.0,
            "mu": 0,
            "sigma": 0,
            "proc_time": 2.0,
            "lead_time_lb": 1.0,
            "lead_time_ub": 3.0
        },
        {
            "name": "最終製品",
            "h": 5.0,
            "mu": 100.0,
            "sigma": 20.0,
            "proc_time": 1.0,
            "lead_time_lb": 0.5,
            "lead_time_ub": 1.5
        }
    ]

    bom_data = [
        {"child": "原材料", "parent": "中間品", "units": 1.0},
        {"child": "中間品", "parent": "最終製品", "units": 1.0}
    ]

    result = execute_mcp_function(
        "dynamic_programming_for_SSA",
        {
            "items_data": items_data,
            "bom_data": bom_data,
            "z": 1.65  # 95%サービスレベル
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")

    if result['status'] == 'error' and 'traceback' in result:
        print(f"\nトレースバック:\n{result['traceback']}")
        raise Exception("動的計画法が失敗しました")

    print(f"総コスト: {result['total_cost']:.2f}")
    print(f"\n保証リードタイム:")
    for name, lt in result['guaranteed_lead_times'].items():
        print(f"  {name}: {lt:.2f}")
    print(f"\n正味補充時間:")
    for name, nrt in result['net_replenishment_times'].items():
        print(f"  {name}: {nrt:.2f}")
    print(f"\n安全在庫レベル:")
    for name, ss in result['safety_stock_levels'].items():
        print(f"  {name}: {ss:.2f}")

    assert result["status"] == "success", "動的計画法が失敗しました"
    assert result["total_cost"] > 0, "総コストが0以下です"
    assert len(result["guaranteed_lead_times"]) == 3, "保証リードタイムが3つありません"

    print("\n✓ テスト合格\n")


def test_4stage_tree():
    """
    4段階ツリー構造での動的計画法テスト
    """
    print("=" * 70)
    print("Test 2: 4段階ツリー構造")
    print("=" * 70)

    items_data = [
        {"name": "原材料A", "h": 0.5, "mu": 0, "sigma": 0, "proc_time": 0.5, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "原材料B", "h": 0.8, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.5, "lead_time_ub": 3.0},
        {"name": "中間品", "h": 2.0, "mu": 0, "sigma": 0, "proc_time": 1.5, "lead_time_lb": 1.0, "lead_time_ub": 2.5},
        {"name": "最終製品", "h": 5.0, "mu": 150.0, "sigma": 25.0, "proc_time": 1.0, "lead_time_lb": 0.5, "lead_time_ub": 1.5}
    ]

    bom_data = [
        {"child": "原材料A", "parent": "中間品", "units": 1.0},
        {"child": "原材料B", "parent": "中間品", "units": 1.0},
        {"child": "中間品", "parent": "最終製品", "units": 1.0}
    ]

    result = execute_mcp_function(
        "dynamic_programming_for_SSA",
        {
            "items_data": items_data,
            "bom_data": bom_data,
            "z": 1.96  # 97.5%サービスレベル
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")
    print(f"総コスト: {result['total_cost']:.2f}")
    print(f"サービスレベル: {result['optimization_params']['service_level']}")

    assert result["status"] == "success", "動的計画法が失敗しました"
    assert len(result["guaranteed_lead_times"]) == 4, "保証リードタイムが4つありません"

    print("\n✓ テスト合格\n")


def test_different_z_values():
    """
    異なるz値（サービスレベル）での動的計画法テスト
    """
    print("=" * 70)
    print("Test 3: 異なるサービスレベルでの比較")
    print("=" * 70)

    items_data = [
        {"name": "原材料", "h": 1.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 2.0, "lead_time_ub": 4.0},
        {"name": "最終製品", "h": 5.0, "mu": 100.0, "sigma": 15.0, "proc_time": 1.0, "lead_time_lb": 0.5, "lead_time_ub": 1.5}
    ]

    bom_data = [
        {"child": "原材料", "parent": "最終製品", "units": 1.0}
    ]

    z_values = [1.28, 1.65, 1.96, 2.33]  # 90%, 95%, 97.5%, 99%

    costs = []
    for z in z_values:
        result = execute_mcp_function(
            "dynamic_programming_for_SSA",
            {
                "items_data": items_data,
                "bom_data": bom_data,
                "z": z
            }
        )

        print(f"\nz={z:.2f} (サービスレベル: {result['optimization_params']['service_level']})")
        print(f"  総コスト: {result['total_cost']:.2f}")
        print(f"  最終製品の安全在庫: {result['safety_stock_levels']['最終製品']:.2f}")

        assert result["status"] == "success", f"z={z}で失敗しました"
        costs.append(result["total_cost"])

    # コストは単調増加するはず
    for i in range(len(costs) - 1):
        assert costs[i] <= costs[i+1], "コストが単調増加していません"

    print("\n✓ テスト合格: コストはサービスレベルに応じて単調増加しています\n")


def test_non_tree_network_error():
    """
    非ツリー構造ネットワークでのエラーテスト
    """
    print("=" * 70)
    print("Test 4: 非ツリー構造ネットワーク（エラー期待）")
    print("=" * 70)

    # 閉路を含むネットワーク
    items_data = [
        {"name": "A", "h": 1.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "B", "h": 2.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "C", "h": 3.0, "mu": 100.0, "sigma": 10.0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0}
    ]

    bom_data = [
        {"child": "A", "parent": "B"},
        {"child": "B", "parent": "C"},
        {"child": "C", "parent": "A"}  # 閉路
    ]

    result = execute_mcp_function(
        "dynamic_programming_for_SSA",
        {
            "items_data": items_data,
            "bom_data": bom_data
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")

    assert result["status"] == "error", "エラーになるべきでした"
    assert "ツリー構造" in result["message"] or "閉路" in result["message"], "ネットワーク構造エラーメッセージが含まれていません"

    print("\n✓ テスト合格: 非ツリー構造が検出されました\n")


def test_deep_tree():
    """
    深い階層のツリー構造での動的計画法テスト
    """
    print("=" * 70)
    print("Test 5: 深い階層のツリー構造（5段階）")
    print("=" * 70)

    items_data = [
        {"name": "Stage0", "h": 0.5, "mu": 0, "sigma": 0, "proc_time": 0.5, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "Stage1", "h": 1.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "Stage2", "h": 2.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "Stage3", "h": 3.0, "mu": 0, "sigma": 0, "proc_time": 1.0, "lead_time_lb": 1.0, "lead_time_ub": 2.0},
        {"name": "Stage4", "h": 5.0, "mu": 200.0, "sigma": 30.0, "proc_time": 1.0, "lead_time_lb": 0.5, "lead_time_ub": 1.5}
    ]

    bom_data = [
        {"child": "Stage0", "parent": "Stage1"},
        {"child": "Stage1", "parent": "Stage2"},
        {"child": "Stage2", "parent": "Stage3"},
        {"child": "Stage3", "parent": "Stage4"}
    ]

    result = execute_mcp_function(
        "dynamic_programming_for_SSA",
        {
            "items_data": items_data,
            "bom_data": bom_data,
            "z": 1.65
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")
    print(f"総コスト: {result['total_cost']:.2f}")

    assert result["status"] == "success", "動的計画法が失敗しました"
    assert len(result["guaranteed_lead_times"]) == 5, "保証リードタイムが5つありません"

    print("\n✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Phase 13-1: 動的計画法による安全在庫配置のテスト開始")
    print("=" * 70 + "\n")

    try:
        test_basic_3stage_tree()
        test_4stage_tree()
        test_different_z_values()
        test_non_tree_network_error()
        test_deep_tree()

        print("\n" + "=" * 70)
        print("全てのテストが合格しました！ ✓")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
