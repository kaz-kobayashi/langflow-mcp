"""
Debug script to investigate (Q,R) policy cost discrepancy
"""
import numpy as np
from scmopt2.optinv import eoq, optimize_qr, optimize_ss, simulate_inventory

# Test parameters from example 9.1
mu = 100  # 需要の平均: 100個/日
sigma = 15  # 需要の標準偏差: 15個/日
LT = 5  # リードタイム: 5日
h = 1  # 在庫保管費用: 1円/個/日
b = 100  # バックオーダーコスト: 100円/個
fc = 500  # 固定発注コスト: 500円
n_samples = 50
n_periods = 200

print("=" * 60)
print("在庫方策の比較テスト")
print("=" * 60)
print(f"パラメータ:")
print(f"  需要平均: {mu}個/日")
print(f"  需要標準偏差: {sigma}個/日")
print(f"  リードタイム: {LT}日")
print(f"  在庫保管費用: {h}円/個/日")
print(f"  バックオーダーコスト: {b}円/個")
print(f"  固定発注コスト: {fc}円")
print(f"  サンプル数: {n_samples}")
print(f"  シミュレーション期間: {n_periods}期")
print()

# 1. EOQ方策
print("=" * 60)
print("1. EOQ方策")
print("=" * 60)
Q_eoq, TC_eoq = eoq(K=fc, d=mu, h=h, b=b, r=0, c=0, theta=0)
print(f"最適発注量 Q*: {Q_eoq:.2f}")
print(f"日次総コスト: {TC_eoq:.2f}円/日")
print()

# 2. (Q,R)方策
print("=" * 60)
print("2. (Q,R)方策")
print("=" * 60)
R_qr, Q_qr = optimize_qr(
    n_samples=n_samples, n_periods=n_periods,
    mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
)
print(f"最適発注量 Q: {Q_qr}")
print(f"最適発注点 R: {R_qr}")

# シミュレーション実行
cost_qr, I_qr = simulate_inventory(
    n_samples=n_samples, n_periods=n_periods,
    mu=mu, sigma=sigma, LT=LT,
    Q=Q_qr, R=R_qr, b=b, h=h, fc=fc
)
print(f"平均コスト: {cost_qr.mean():.2f}円/日")
print(f"コスト標準偏差: {cost_qr.std():.2f}円/日")
print()

# 3. (s,S)方策
print("=" * 60)
print("3. (s,S)方策")
print("=" * 60)
s_ss, S_ss = optimize_ss(
    n_samples=n_samples, n_periods=n_periods,
    mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
)
print(f"最適発注点 s: {s_ss}")
print(f"最適目標在庫 S: {S_ss}")

# シミュレーション実行
cost_ss, I_ss = simulate_inventory(
    n_samples=n_samples, n_periods=n_periods,
    mu=mu, sigma=sigma, LT=LT,
    Q=None, R=s_ss, b=b, h=h, fc=fc, S=S_ss
)
print(f"平均コスト: {cost_ss.mean():.2f}円/日")
print(f"コスト標準偏差: {cost_ss.std():.2f}円/日")
print()

# 比較
print("=" * 60)
print("コスト比較")
print("=" * 60)
print(f"EOQ方策:   {TC_eoq:.2f}円/日")
print(f"(Q,R)方策: {cost_qr.mean():.2f}円/日")
print(f"(s,S)方策: {cost_ss.mean():.2f}円/日")
print()

if cost_qr.mean() > TC_eoq * 5:
    print("⚠️  警告: (Q,R)方策のコストが異常に高い!")
    print(f"   EOQの{cost_qr.mean()/TC_eoq:.1f}倍です")

    # 詳細デバッグ: EOQパラメータで(Q,R)シミュレーションを実行
    print()
    print("=" * 60)
    print("デバッグ: EOQパラメータで(Q,R)シミュレーション")
    print("=" * 60)
    omega = b/(b+h)
    z = np.sqrt(2) * 0.99  # approximation of norm.ppf(omega)
    R_debug = int(LT*mu + z*sigma*np.sqrt(LT))
    cost_debug, _ = simulate_inventory(
        n_samples=n_samples, n_periods=n_periods,
        mu=mu, sigma=sigma, LT=LT,
        Q=int(Q_eoq), R=R_debug, b=b, h=h, fc=fc
    )
    print(f"Q={int(Q_eoq)}, R={R_debug}")
    print(f"シミュレーションコスト: {cost_debug.mean():.2f}円/日")
