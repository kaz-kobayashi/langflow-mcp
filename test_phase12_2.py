"""
Phase 12-2: シミュレーション軌道可視化機能のテスト
"""
import sys
sys.path.append('.')

import numpy as np
import pandas as pd
from scmopt2.optinv import plot_simulation


def test_basic_trajectory_visualization():
    """
    基本的な軌道可視化のテスト
    """
    print("=" * 60)
    print("Test 1: 基本的な軌道可視化")
    print("=" * 60)

    # シミュレーションデータを生成
    n_samples = 10
    n_stages = 3
    n_periods = 50

    # 在庫データ（ランダムウォーク風）
    I = np.zeros((n_samples, n_stages, n_periods + 1))

    for sample in range(n_samples):
        for stage in range(n_stages):
            I[sample, stage, 0] = 100 + stage * 50  # 初期在庫
            for t in range(n_periods):
                # ランダムウォーク
                change = np.random.normal(0, 10)
                I[sample, stage, t + 1] = max(0, I[sample, stage, t] + change)

    # stage_dfの作成
    stage_df = pd.DataFrame({
        "name": ["サプライヤー", "工場", "製品"]
    })

    # グラフ作成
    fig = plot_simulation(stage_df, I, n_periods=n_periods, samples=5)

    assert fig is not None, "グラフが生成されませんでした"

    # HTMLとして保存
    fig.write_html("/tmp/test_trajectory_basic.html")
    print(f"✓ 基本軌道可視化を保存: /tmp/test_trajectory_basic.html")
    print("✓ テスト合格\n")


def test_selected_stages():
    """
    特定の段階のみを表示するテスト
    """
    print("=" * 60)
    print("Test 2: 特定段階のみ表示")
    print("=" * 60)

    # 5段階のシミュレーションデータ
    n_samples = 8
    n_stages = 5
    n_periods = 30

    I = np.zeros((n_samples, n_stages, n_periods + 1))

    for sample in range(n_samples):
        for stage in range(n_stages):
            I[sample, stage, 0] = 200 - stage * 20
            for t in range(n_periods):
                change = np.random.normal(-2, 15)
                I[sample, stage, t + 1] = max(0, I[sample, stage, t] + change)

    stage_df = pd.DataFrame({
        "name": ["段階0", "段階1", "段階2", "段階3", "段階4"]
    })

    # 段階1, 3, 4のみ表示
    stage_id_list = [1, 3, 4]
    fig = plot_simulation(stage_df, I, n_periods=n_periods, samples=5, stage_id_list=stage_id_list)

    assert fig is not None, "グラフが生成されませんでした"

    fig.write_html("/tmp/test_trajectory_selected.html")
    print(f"✓ 選択段階可視化を保存: /tmp/test_trajectory_selected.html")
    print(f"✓ 表示段階: {stage_id_list}")
    print("✓ テスト合格\n")


def test_few_samples():
    """
    サンプル数が少ない場合のテスト
    """
    print("=" * 60)
    print("Test 3: 少数サンプル")
    print("=" * 60)

    n_samples = 3
    n_stages = 2
    n_periods = 40

    I = np.zeros((n_samples, n_stages, n_periods + 1))

    # 各サンプルで異なるパターン
    patterns = [
        {"trend": 5, "volatility": 5},   # 増加傾向・低変動
        {"trend": -3, "volatility": 10}, # 減少傾向・中変動
        {"trend": 0, "volatility": 20}   # 横ばい・高変動
    ]

    for sample in range(n_samples):
        pattern = patterns[sample]
        for stage in range(n_stages):
            I[sample, stage, 0] = 150
            for t in range(n_periods):
                change = np.random.normal(pattern["trend"], pattern["volatility"])
                I[sample, stage, t + 1] = max(0, I[sample, stage, t] + change)

    stage_df = pd.DataFrame({
        "name": ["倉庫", "店舗"]
    })

    fig = plot_simulation(stage_df, I, n_periods=n_periods, samples=3)

    assert fig is not None, "グラフが生成されませんでした"

    fig.write_html("/tmp/test_trajectory_few_samples.html")
    print(f"✓ 少数サンプル可視化を保存: /tmp/test_trajectory_few_samples.html")
    print(f"✓ サンプル数: {n_samples}")
    print("✓ テスト合格\n")


def test_with_stockouts():
    """
    品切れを含むシミュレーション軌道のテスト
    """
    print("=" * 60)
    print("Test 4: 品切れを含む軌道")
    print("=" * 60)

    n_samples = 10
    n_stages = 3
    n_periods = 60

    I = np.zeros((n_samples, n_stages, n_periods + 1))

    for sample in range(n_samples):
        for stage in range(n_stages):
            I[sample, stage, 0] = 100
            for t in range(n_periods):
                # 需要変動が大きく、品切れが発生しやすい
                demand = np.random.normal(10, 15)
                supply = np.random.normal(8, 5)
                I[sample, stage, t + 1] = I[sample, stage, t] + supply - demand

    stage_df = pd.DataFrame({
        "name": ["原材料", "仕掛品", "完成品"]
    })

    fig = plot_simulation(stage_df, I, n_periods=n_periods, samples=5)

    assert fig is not None, "グラフが生成されませんでした"

    # 品切れ回数を計算
    for stage in range(n_stages):
        stockout_count = (I[:, stage, :] < 0).sum()
        print(f"  {stage_df['name'][stage]}: 品切れ回数 = {stockout_count}")

    fig.write_html("/tmp/test_trajectory_stockouts.html")
    print(f"\n✓ 品切れ含む可視化を保存: /tmp/test_trajectory_stockouts.html")
    print("✓ テスト合格\n")


def test_long_simulation():
    """
    長期間シミュレーションのテスト
    """
    print("=" * 60)
    print("Test 5: 長期間シミュレーション")
    print("=" * 60)

    n_samples = 5
    n_stages = 4
    n_periods = 200  # 長期間

    I = np.zeros((n_samples, n_stages, n_periods + 1))

    for sample in range(n_samples):
        for stage in range(n_stages):
            I[sample, stage, 0] = 300 + stage * 100
            for t in range(n_periods):
                # 長期トレンドと季節変動
                trend = -0.1 * t  # 緩やかな減少
                seasonal = 50 * np.sin(2 * np.pi * t / 50)  # 季節変動
                noise = np.random.normal(0, 20)
                I[sample, stage, t + 1] = max(50, I[sample, stage, 0] + trend + seasonal + noise)

    stage_df = pd.DataFrame({
        "name": ["原料倉庫", "加工工場", "配送センター", "小売店"]
    })

    fig = plot_simulation(stage_df, I, n_periods=n_periods, samples=3)

    assert fig is not None, "グラフが生成されませんでした"

    # 統計情報
    print(f"  シミュレーション期間: {n_periods}")
    print(f"  データポイント数: {n_samples * n_stages * (n_periods + 1):,}")

    fig.write_html("/tmp/test_trajectory_long.html")
    print(f"\n✓ 長期間可視化を保存: /tmp/test_trajectory_long.html")
    print("✓ テスト合格\n")


def test_multistage_with_real_simulation():
    """
    実際の多段階シミュレーション結果の可視化テスト
    """
    print("=" * 60)
    print("Test 6: 実際のシミュレーション結果可視化")
    print("=" * 60)

    from scmopt2.optinv import simulate_multistage_ss_policy

    # 実際のシミュレーションを実行
    np.random.seed(42)
    avg_cost, inventory_data, total_cost = simulate_multistage_ss_policy(
        n_samples=10,
        n_periods=50,
        n_stages=3,
        mu=100.,
        sigma=10.,
        LT=[2, 1, 1],
        s=[150., 100., 100.],
        S=[250., 180., 180.],
        b=100.,
        h=[1., 2., 5.],
        fc=1000.
    )

    print(f"平均コスト: {avg_cost:.2f}")

    stage_df = pd.DataFrame({
        "name": ["サプライヤー", "工場", "製品"]
    })

    # 可視化
    fig = plot_simulation(stage_df, inventory_data, n_periods=50, samples=5)

    assert fig is not None, "グラフが生成されませんでした"

    fig.write_html("/tmp/test_trajectory_real_simulation.html")
    print(f"✓ 実シミュレーション可視化を保存: /tmp/test_trajectory_real_simulation.html")
    print("✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 12-2: シミュレーション軌道可視化機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_basic_trajectory_visualization()
        test_selected_stages()
        test_few_samples()
        test_with_stockouts()
        test_long_simulation()
        test_multistage_with_real_simulation()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
