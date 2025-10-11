"""
Manual calculation of (Q,R) parameters
"""
import numpy as np
from scipy.stats import norm

# Test parameters
mu = 100  # daily demand
sigma = 15  # demand std dev
LT = 5  # lead time days
h = 1  # holding cost
b = 100  # backorder cost
fc = 500  # fixed cost

# Calculate critical ratio and safety factor
omega = b/(b+h)
z = norm.ppf(omega)

print("=" * 60)
print("Manual (Q,R) Parameter Calculation")
print("=" * 60)
print(f"Critical ratio (omega): {omega:.4f}")
print(f"Safety factor (z): {z:.4f}")
print()

# Calculate EOQ
Q_eoq = np.sqrt(2*fc*mu/h/omega)
print(f"EOQ (Q*): {Q_eoq:.2f}")
print()

# Calculate reorder point
R = LT*mu + z*sigma*np.sqrt(LT)
print(f"Reorder point formula: R = LT*mu + z*sigma*sqrt(LT)")
print(f"R = {LT}*{mu} + {z:.4f}*{sigma}*sqrt({LT})")
print(f"R = {LT*mu} + {z*sigma*np.sqrt(LT):.2f}")
print(f"R = {R:.2f}")
print()

print("Expected (Q,R) parameters:")
print(f"  Q = {Q_eoq:.2f}")
print(f"  R = {R:.2f}")
