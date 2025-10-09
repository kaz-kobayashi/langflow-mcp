"""
Phase 13-2: 分布ベースの基在庫シミュレーションのテスト
"""
import sys
sys.path.append('.')

from mcp_tools import execute_mcp_function

def test_normal_distribution():
    """
    正規分布での基在庫シミュレーションテスト
    """
    print("=" * 70)
    print("Test 1: 正規分布での基在庫シミュレーション")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "normal",
                "params": {"mu": 100, "sigma": 10}
            },
            "lead_time": 2,
            "backorder_cost": 100,
            "holding_cost": 1
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")
    print(f"基在庫レベル: {result['base_stock_level']:.2f}")
    print(f"平均コスト: {result['average_cost']:.2f}")
    print(f"勾配: {result['gradient']:.2f}")
    print(f"\n在庫統計:")
    for key, value in result['inventory_stats'].items():
        print(f"  {key}: {value:.2f}")

    assert result["status"] == "success", "シミュレーションが失敗しました"
    assert result["average_cost"] > 0, "平均コストが0以下です"

    print("\n✓ テスト合格\n")


def test_uniform_distribution():
    """
    一様分布での基在庫シミュレーションテスト
    """
    print("=" * 70)
    print("Test 2: 一様分布での基在庫シミュレーション")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "uniform",
                "params": {"low": 80, "high": 120}
            },
            "lead_time": 1,
            "backorder_cost": 150,
            "holding_cost": 2,
            "base_stock_level": 250  # 明示的に指定
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"平均コスト: {result['average_cost']:.2f}")
    print(f"基在庫レベル: {result['base_stock_level']:.2f}")
    print(f"品切れ率: {result['inventory_stats']['stockout_rate']:.2%}")

    assert result["status"] == "success", "シミュレーションが失敗しました"
    assert result["base_stock_level"] == 250, "基在庫レベルが指定値と異なります"

    print("\n✓ テスト合格\n")


def test_poisson_distribution():
    """
    ポアソン分布での基在庫シミュレーションテスト
    """
    print("=" * 70)
    print("Test 3: ポアソン分布での基在庫シミュレーション")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "poisson",
                "params": {"lam": 100}
            },
            "capacity": 200,  # 生産能力制約
            "lead_time": 2
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"平均コスト: {result['average_cost']:.2f}")
    print(f"生産能力: {result['simulation_params']['capacity']:.0f}")

    assert result["status"] == "success", "シミュレーションが失敗しました"

    print("\n✓ テスト合格\n")


def test_gamma_distribution():
    """
    ガンマ分布での基在庫シミュレーションテスト
    """
    print("=" * 70)
    print("Test 4: ガンマ分布での基在庫シミュレーション")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "gamma",
                "params": {"shape": 4, "scale": 25}
            },
            "lead_time": 3
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"分布タイプ: {result['simulation_params']['demand_distribution']}")
    print(f"平均コスト: {result['average_cost']:.2f}")

    assert result["status"] == "success", "シミュレーションが失敗しました"
    assert result["simulation_params"]["demand_distribution"] == "gamma"

    print("\n✓ テスト合格\n")


def test_lognormal_distribution():
    """
    対数正規分布での基在庫シミュレーションテスト
    """
    print("=" * 70)
    print("Test 5: 対数正規分布での基在庫シミュレーション")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "lognormal",
                "params": {"s": 0.3, "scale": 100}
            },
            "lead_time": 2,
            "backorder_cost": 200,
            "holding_cost": 3
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"平均コスト: {result['average_cost']:.2f}")
    print(f"平均在庫: {result['inventory_stats']['mean_inventory']:.2f}")

    assert result["status"] == "success", "シミュレーションが失敗しました"

    print("\n✓ テスト合格\n")


def test_unsupported_distribution():
    """
    サポートされていない分布でのエラーテスト
    """
    print("=" * 70)
    print("Test 6: サポートされていない分布（エラー期待）")
    print("=" * 70)

    result = execute_mcp_function(
        "base_stock_simulation_using_dist",
        {
            "n_samples": 50,
            "n_periods": 100,
            "demand_dist": {
                "type": "unknown_dist",
                "params": {}
            }
        }
    )

    print(f"\n結果: {result['status']}")
    print(f"メッセージ: {result['message']}")

    assert result["status"] == "error", "エラーになるべきでした"
    assert "サポートされていない" in result["message"], "適切なエラーメッセージが表示されていません"

    print("\n✓ テスト合格: 未サポート分布が検出されました\n")


def test_different_lead_times():
    """
    異なるリードタイムでの比較テスト
    """
    print("=" * 70)
    print("Test 7: 異なるリードタイムでの比較")
    print("=" * 70)

    lead_times = [1, 2, 3, 5]
    costs = []

    for lt in lead_times:
        result = execute_mcp_function(
            "base_stock_simulation_using_dist",
            {
                "n_samples": 50,
                "n_periods": 100,
                "demand_dist": {
                    "type": "normal",
                    "params": {"mu": 100, "sigma": 10}
                },
                "lead_time": lt,
                "backorder_cost": 100,
                "holding_cost": 1
            }
        )

        print(f"\nリードタイム={lt}:")
        print(f"  基在庫レベル: {result['base_stock_level']:.2f}")
        print(f"  平均コスト: {result['average_cost']:.2f}")

        assert result["status"] == "success", f"リードタイム={lt}で失敗しました"
        costs.append(result["average_cost"])

    # リードタイムが長いほどコストが高くなる傾向
    print("\n✓ テスト合格: 異なるリードタイムでのシミュレーションが完了しました\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Phase 13-2: 分布ベースの基在庫シミュレーションのテスト開始")
    print("=" * 70 + "\n")

    try:
        test_normal_distribution()
        test_uniform_distribution()
        test_poisson_distribution()
        test_gamma_distribution()
        test_lognormal_distribution()
        test_unsupported_distribution()
        test_different_lead_times()

        print("\n" + "=" * 70)
        print("全てのテストが合格しました！ ✓")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
