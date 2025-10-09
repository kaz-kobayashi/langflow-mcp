"""
Phase 11-2: ヒストグラム分布フィット機能のテスト
"""
import sys
sys.path.append('.')

import numpy as np
from scmopt2.optinv import best_histogram


def test_normal_distribution():
    """
    正規分布データでのヒストグラムフィットテスト
    """
    print("=" * 60)
    print("Test 1: 正規分布データのヒストグラムフィット")
    print("=" * 60)

    # 正規分布データを生成
    np.random.seed(42)
    data = np.random.normal(100, 10, 1000)

    fig, hist_dist = best_histogram(data, nbins=20)

    assert fig is not None, "グラフが生成されませんでした"
    assert hist_dist is not None, "ヒストグラム分布が生成されませんでした"

    # 分布の統計量を確認
    mean = hist_dist.mean()
    std = hist_dist.std()

    print(f"データの平均: {data.mean():.2f}")
    print(f"フィット分布の平均: {mean:.2f}")
    print(f"データの標準偏差: {data.std():.2f}")
    print(f"フィット分布の標準偏差: {std:.2f}")

    # グラフを保存
    fig.write_html("/tmp/test_histogram_normal.html")
    print(f"✓ グラフを保存: /tmp/test_histogram_normal.html")
    print("✓ テスト合格\n")


def test_uniform_distribution():
    """
    一様分布データでのヒストグラムフィットテスト
    """
    print("=" * 60)
    print("Test 2: 一様分布データのヒストグラムフィット")
    print("=" * 60)

    # 一様分布データを生成
    np.random.seed(42)
    data = np.random.uniform(50, 150, 1000)

    fig, hist_dist = best_histogram(data, nbins=30)

    assert fig is not None, "グラフが生成されませんでした"
    assert hist_dist is not None, "ヒストグラム分布が生成されませんでした"

    # 分布の統計量を確認
    mean = hist_dist.mean()

    print(f"データの平均: {data.mean():.2f}")
    print(f"フィット分布の平均: {mean:.2f}")

    # グラフを保存
    fig.write_html("/tmp/test_histogram_uniform.html")
    print(f"✓ グラフを保存: /tmp/test_histogram_uniform.html")
    print("✓ テスト合格\n")


def test_exponential_distribution():
    """
    指数分布データでのヒストグラムフィットテスト
    """
    print("=" * 60)
    print("Test 3: 指数分布データのヒストグラムフィット")
    print("=" * 60)

    # 指数分布データを生成
    np.random.seed(42)
    data = np.random.exponential(50, 1000)

    fig, hist_dist = best_histogram(data, nbins=40)

    assert fig is not None, "グラフが生成されませんでした"
    assert hist_dist is not None, "ヒストグラム分布が生成されませんでした"

    # 分布の統計量を確認
    mean = hist_dist.mean()

    print(f"データの平均: {data.mean():.2f}")
    print(f"フィット分布の平均: {mean:.2f}")

    # グラフを保存
    fig.write_html("/tmp/test_histogram_exponential.html")
    print(f"✓ グラフを保存: /tmp/test_histogram_exponential.html")
    print("✓ テスト合格\n")


def test_different_bin_sizes():
    """
    異なるビン数でのテスト
    """
    print("=" * 60)
    print("Test 4: 異なるビン数での比較")
    print("=" * 60)

    # データを生成
    np.random.seed(42)
    data = np.random.normal(100, 15, 1000)

    bin_sizes = [10, 25, 50, 100]

    for nbins in bin_sizes:
        fig, hist_dist = best_histogram(data, nbins=nbins)

        assert fig is not None, f"nbins={nbins}でグラフが生成されませんでした"
        assert hist_dist is not None, f"nbins={nbins}でヒストグラム分布が生成されませんでした"

        mean = hist_dist.mean()
        std = hist_dist.std()

        print(f"  nbins={nbins}: 平均={mean:.2f}, 標準偏差={std:.2f}")

        filename = f"/tmp/test_histogram_bins_{nbins}.html"
        fig.write_html(filename)

    print(f"✓ 異なるビン数でのテスト完了")
    print("✓ テスト合格\n")


def test_small_dataset():
    """
    小さいデータセットでのテスト
    """
    print("=" * 60)
    print("Test 5: 小さいデータセット")
    print("=" * 60)

    # 小さいデータセット
    np.random.seed(42)
    data = np.random.normal(50, 5, 50)  # 50個のデータ

    fig, hist_dist = best_histogram(data, nbins=10)

    assert fig is not None, "グラフが生成されませんでした"
    assert hist_dist is not None, "ヒストグラム分布が生成されませんでした"

    print(f"データ数: {len(data)}")
    print(f"データの平均: {data.mean():.2f}")
    print(f"フィット分布の平均: {hist_dist.mean():.2f}")

    fig.write_html("/tmp/test_histogram_small.html")
    print(f"✓ グラフを保存: /tmp/test_histogram_small.html")
    print("✓ テスト合格\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Phase 11-2: ヒストグラム分布フィット機能のテスト開始")
    print("=" * 60 + "\n")

    try:
        test_normal_distribution()
        test_uniform_distribution()
        test_exponential_distribution()
        test_different_bin_sizes()
        test_small_dataset()

        print("\n" + "=" * 60)
        print("全てのテストが合格しました！ ✓")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
