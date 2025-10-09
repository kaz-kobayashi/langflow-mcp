"""
Phase 11-3: 多段階在庫シミュレーション機能のテスト
"""
import sys
sys.path.append('.')

import numpy as np
from scmopt2.optinv import simulate_multistage_ss_policy


def test_basic_multistage_simulation():
    """
    基本的な多段階シミュレーションのテスト
    """
    print("=" * 60)
    print("Test 1: 基本的な3段階シミュレーション")
    print("=" * 60)

    # 3段階サプライチェーン
    avg_cost, inventory_data, total_cost = simulate_multistage_ss_policy(
        n_samples=10,
        n_periods=50,
        n_stages=3,
        mu=100.,
        sigma=10.,
        LT=[1, 1, 1],
        b=100.,
        h=[1., 2., 5.],
        fc=1000.
    )

    print(f"平均コスト: {avg_cost:.2f}")
    print(f"在庫データの形状: {inventory_data.shape}")
    print(f"サンプル別総コスト形状: {total_cost.shape}")

    assert avg_cost > 0, "平均コストが正の値ではありません"
    assert inventory_data.shape == (10, 3, 51), "在庫データの形状が不正です"
    assert total_cost.shape == (10,), "総コストの形状が不正です"

    print("✓ テスト合格\n")


def test_with_specified_policy():
    """
    明示的な(s,S)パラメータでのテスト
    """
    print("=" * 60)
    print("Test 2: 明示的な(s,S)パラメータ指定")
    print("=" * 60)

    # パラメータを明示的に指定
    avg_cost, inventory_data, total_cost = simulate_multistage_ss_policy(
        n_samples=10,
        n_periods=100,
        n_stages=3,
        mu=100.,
        sigma=15.,
        LT=[2, 1, 1],
        s=[150., 100., 100.],
        S=[250., 180., 180.],
        b=100.,
        h=[1., 2., 5.],
        fc=1000.
    )

    print(f"平均コスト: {avg_cost:.2f}")
    print(f"総コストの平均: {total_cost.mean():.2f}")
    print(f"総コストの標準偏差: {total_cost.std():.2f}")

    assert avg_cost > 0, "平均コストが正の値ではありません"
    print("✓ テスト合格\n")


def test_different_stage_numbers():
    """
    異なる段階数でのテスト
    """
    print("=" * 60)
    print("Test 3: 異なる段階数での比較")
    print("=" * 60)

    stage_numbers = [2, 3, 4, 5]
    results = []

    for n_stages in stage_numbers:
        avg_cost, _, _ = simulate_multistage_ss_policy(
            n_samples=5,
            n_periods=50,
            n_stages=n_stages,
            mu=100.,
            sigma=10.,
            LT=np.ones(n_stages, dtype=int).tolist(),
            b=100.,
            h=np.arange(1, n_stages + 1).tolist(),
            fc=1000.
        )
        results.append({"n_stages": n_stages, "avg_cost": avg_cost})
        print(f"  {n_stages}段階: 平均コスト = {avg_cost:.2f}")

    assert len(results) == 4, "結果の数が正しくありません"
    print("✓ テスト合格\n")


def test_varying_demand():
    """
    異なる需要パラメータでのテスト
    """
    print("=" * 60)
    print("Test 4: 異なる需要パラメータ")
    print("=" * 60)

    demand_scenarios = [
        {"mu": 50, "sigma": 5, "name": "低需要・低変動"},
        {"mu": 100, "sigma": 10, "name": "中需要・中変動"},
        {"mu": 200, "sigma": 30, "name": "高需要・高変動"}
    ]

    for scenario in demand_scenarios:
        avg_cost, _, _ = simulate_multistage_ss_policy(
            n_samples=10,
            n_periods=50,
            n_stages=3,
            mu=scenario["mu"],
            sigma=scenario["sigma"],
            b=100.,
            h=[1., 2., 5.],
            fc=1000.
        )
        print(f"  {scenario['name']}: 平均コスト = {avg_cost:.2f}")

    print("✓ テスト合格\n")


def test_inventory_trajectory():
    """
    在庫推移の確認テスト
    """
    print("=" * 60)
    print("Test 5: 在庫推移の確認")
    print("=" * 60)

    np.random.seed(42)  # 再現性のため
    avg_cost, inventory_data, _ = simulate_multistage_ss_policy(
        n_samples=1,
        n_periods=20,
        n_stages=3,
        mu=100.,
        sigma=10.,
        LT=[1, 1, 1],
        s=[100., 100., 100.],
        S=[200., 200., 200.],
        b=100.,
        h=[1., 2., 5.],
        fc=1000.
    )

    # サンプル0の各段階の在庫推移を表示
    print("  サンプル0の在庫推移（最初の10期）:")
    for i in range(3):
        inv = inventory_data[0, i, :11]
        print(f"    段階{i}: {inv}")

    # 在庫が極端な値にならないことを確認
    max_inv = inventory_data.max()
    min_inv = inventory_data.min()
    print(f"\n  最大在庫: {max_inv:.2f}")
    print(f"  最小在庫: {min_inv:.2f}")

    assert max_inv < 10000, "在庫が異常に大きい値です"
    assert min_inv > -5000, "在庫が異常に小さい値です"

    print("✓ テスト合格\n")


def test_lead_time_impact():
    """
    リードタイムの影響を確認するテスト
    """
    print("=" * 60)
    print("Test 6: リードタイムの影響")
    print("=" * 60)

    lead_time_scenarios = [
        {"LT": [1, 1, 1], "name": "短いリードタイム"},
        {"LT": [2, 2, 2], "name": "中程度のリードタイム"},
        {"LT": [3, 3, 3], "name": "長いリードタイム"}
    ]

    for scenario in lead_time_scenarios:
        avg_cost, _, _ = simulate_multistage_ss_policy(
            n_samples=10,
            n_periods=50,
            n_stages=3,
            mu=100.,
            sigma=10.,
            LT=scenario["LT"],
            b=100.,
            h=[1., 2., 5.],
            fc=1000.
        )
        print(f"  {scenario['name']}: 平均コスト = {avg_cost:.2f}")

    print("✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 11-3: 多段階在庫シミュレーション機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_basic_multistage_simulation()
        test_with_specified_policy()
        test_different_stage_numbers()
        test_varying_demand()
        test_inventory_trajectory()
        test_lead_time_impact()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
