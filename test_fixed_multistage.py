"""
修正版多段階シミュレーション関数のテスト
"""

import numpy as np
from fixed_multistage import (
    multi_stage_simulate_inventory_fixed,
    base_stock_simulation_fixed,
    multi_stage_base_stock_simulation_fixed,
    initial_base_stock_level_fixed
)

print("=" * 60)
print("Test 1: multi_stage_simulate_inventory_fixed")
print("=" * 60)

# 3段階サプライチェーン（原材料 → 工場 → 小売）
LT = np.array([2, 3, 1])  # 各段階のリードタイム
h = np.array([1.0, 2.0, 5.0])  # 各段階の在庫保管費用

try:
    cost, I, T = multi_stage_simulate_inventory_fixed(
        n_samples=10,
        n_periods=100,
        mu=10.0,
        sigma=2.0,
        LT=LT,
        s=None,  # 自動計算
        S=None,  # 自動計算
        b=100.0,
        h=h,
        fc=50.0
    )
    print(f"✅ Success!")
    print(f"  Average cost: {cost.mean():.2f} ± {cost.std():.2f}")
    print(f"  Inventory shape: {I.shape}")
    print(f"  Transport shape: {T.shape}")
    print(f"  Final inventory levels: {I[0, :, -1]}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 2: base_stock_simulation_fixed")
print("=" * 60)

# 単一段階、1次元需要データ
demand_1d = np.random.normal(10, 2, 100)

try:
    dC, total_cost, I = base_stock_simulation_fixed(
        n_samples=5,
        n_periods=50,
        demand=demand_1d,
        capacity=1000,
        LT=3,
        b=100.0,
        h=1.0,
        S=50.0
    )
    print(f"✅ Success!")
    print(f"  Derivative: {dC:.4f}")
    print(f"  Total cost: {total_cost:.2f}")
    print(f"  Inventory shape: {I.shape}")
    print(f"  Final inventory: {I[:, -1]}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 3: base_stock_simulation_fixed (2D demand)")
print("=" * 60)

# 2次元需要データ
demand_2d = np.random.normal(10, 2, (5, 50))

try:
    dC, total_cost, I = base_stock_simulation_fixed(
        n_samples=5,
        n_periods=50,
        demand=demand_2d,
        capacity=1000,
        LT=3,
        b=100.0,
        h=1.0,
        S=50.0
    )
    print(f"✅ Success!")
    print(f"  Derivative: {dC:.4f}")
    print(f"  Total cost: {total_cost:.2f}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 4: multi_stage_base_stock_simulation_fixed")
print("=" * 60)

# 2段階システム
LT_2stage = np.array([2, 3])
h_2stage = np.array([1.0, 3.0])
S_2stage = np.array([50.0, 80.0])
capacity_2stage = np.array([1000, 1000])
demand_2stage = np.random.normal(10, 2, 50)

try:
    dC, total_cost, I = multi_stage_base_stock_simulation_fixed(
        n_samples=5,
        n_periods=50,
        demand=demand_2stage,
        capacity=capacity_2stage,
        LT=LT_2stage,
        b=100.0,
        h=h_2stage,
        S=S_2stage
    )
    print(f"✅ Success!")
    print(f"  Derivatives: {dC[0]}")
    print(f"  Total cost: {total_cost:.2f}")
    print(f"  Inventory shape: {I.shape}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test 5: initial_base_stock_level_fixed")
print("=" * 60)

# ネットワーク構造のリードタイム
LT_dict = {
    'supplier': 5,
    'warehouse': 3,
    'retailer': 1
}

try:
    S_dict, ELT_dict = initial_base_stock_level_fixed(
        LT_dict=LT_dict,
        mu=10.0,
        z=1.65,  # 95% service level
        sigma=2.0
    )
    print(f"✅ Success!")
    print(f"  Base stock levels:")
    for node, s in S_dict.items():
        print(f"    {node}: {s:.2f}")
    print(f"  Echelon lead times:")
    for node, elt in ELT_dict.items():
        print(f"    {node}: {elt}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
