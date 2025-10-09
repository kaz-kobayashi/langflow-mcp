"""
キャッシュ機構のテスト - シミュレーション結果の保存と再利用
"""
import sys
sys.path.append('.')

# mcp_toolsのexecute_mcp_function関数をテスト
from mcp_tools import execute_mcp_function

def test_cache_simulation_and_visualize():
    """
    シミュレーション実行→結果をキャッシュ→可視化の流れをテスト
    """
    print("=" * 70)
    print("Test: シミュレーション結果のキャッシュと可視化")
    print("=" * 70)

    user_id = 12345  # テスト用のユーザーID

    # ステップ1: シミュレーション実行
    print("\nステップ1: シミュレーション実行")
    sim_result = execute_mcp_function(
        "simulate_multistage_inventory",
        {
            "n_samples": 5,
            "n_periods": 50,
            "n_stages": 3,
            "mu": 100,
            "sigma": 10,
            "LT": [2, 1, 1],
            "s": [150, 100, 100],
            "S": [250, 180, 180],
            "h": [1, 2, 5],
            "b": 100,
            "fc": 1000
        },
        user_id=user_id
    )

    print(f"シミュレーション結果: {sim_result['status']}")
    print(f"メッセージ: {sim_result['message']}")
    print(f"平均コスト: {sim_result['average_cost']:.2f}")

    assert sim_result["status"] == "success", "シミュレーションが失敗しました"
    assert "結果は保存されました" in sim_result["message"], "キャッシュメッセージが含まれていません"

    # ステップ2: inventory_dataを指定せずに可視化（キャッシュから自動取得）
    print("\nステップ2: キャッシュから可視化")
    viz_result = execute_mcp_function(
        "visualize_simulation_trajectories",
        {
            "samples": 3,
            "stage_names": ["サプライヤー", "工場", "製品"]
        },
        user_id=user_id
    )

    print(f"可視化結果: {viz_result['status']}")
    print(f"メッセージ: {viz_result['message']}")
    print(f"可視化ID: {viz_result.get('visualization_id', 'N/A')}")

    assert viz_result["status"] == "success", "可視化が失敗しました"
    assert "visualization_id" in viz_result, "可視化IDが生成されていません"

    print("\n✓ テスト合格: キャッシュ機構が正常に動作しています\n")


def test_cache_without_simulation():
    """
    シミュレーション実行なしで可視化を試みる（エラーになるべき）
    """
    print("=" * 70)
    print("Test: シミュレーション未実行での可視化")
    print("=" * 70)

    user_id = 99999  # 新規ユーザー（キャッシュなし）

    # シミュレーション実行なしで可視化を試みる
    viz_result = execute_mcp_function(
        "visualize_simulation_trajectories",
        {
            "samples": 3
        },
        user_id=user_id
    )

    print(f"結果: {viz_result['status']}")
    print(f"メッセージ: {viz_result['message']}")

    assert viz_result["status"] == "error", "エラーになるべきでした"
    assert "キャッシュにも保存されたシミュレーション結果がありません" in viz_result["message"], "適切なエラーメッセージが表示されていません"

    print("\n✓ テスト合格: キャッシュがない場合に適切にエラーが返されます\n")


def test_multiple_simulations():
    """
    複数回シミュレーションを実行して、最新の結果が使われることを確認
    """
    print("=" * 70)
    print("Test: 複数シミュレーションでの最新結果使用")
    print("=" * 70)

    user_id = 54321

    # シミュレーション1: 3段階
    print("\nシミュレーション1: 3段階")
    sim1 = execute_mcp_function(
        "simulate_multistage_inventory",
        {
            "n_samples": 5,
            "n_periods": 30,
            "n_stages": 3,
            "mu": 80
        },
        user_id=user_id
    )
    print(f"  段階数: {sim1['simulation_params']['n_stages']}")

    # シミュレーション2: 4段階（上書き）
    print("\nシミュレーション2: 4段階")
    sim2 = execute_mcp_function(
        "simulate_multistage_inventory",
        {
            "n_samples": 5,
            "n_periods": 30,
            "n_stages": 4,
            "mu": 100
        },
        user_id=user_id
    )
    print(f"  段階数: {sim2['simulation_params']['n_stages']}")

    # 可視化（最新の4段階シミュレーションが使われるべき）
    print("\n可視化: 最新のシミュレーション結果を使用")
    viz = execute_mcp_function(
        "visualize_simulation_trajectories",
        {"samples": 3},
        user_id=user_id
    )

    print(f"  可視化された段階数: {viz['params']['n_stages']}")

    assert viz["params"]["n_stages"] == 4, "最新のシミュレーション結果が使われていません"

    print("\n✓ テスト合格: 最新のシミュレーション結果が正しく使用されます\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("キャッシュ機構のテスト開始")
    print("=" * 70 + "\n")

    try:
        test_cache_simulation_and_visualize()
        test_cache_without_simulation()
        test_multiple_simulations()

        print("\n" + "=" * 70)
        print("全てのテストが合格しました！ ✓")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
