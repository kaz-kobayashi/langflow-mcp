"""
Direct test of optimize_qr function return order
"""
import numpy as np
from scmopt2.optinv import optimize_qr

# Test parameters
mu = 100
sigma = 15
LT = 5
h = 1
b = 100
fc = 500
n_samples = 50
n_periods = 200

print("Testing optimize_qr return order...")
result = optimize_qr(
    n_samples=n_samples, n_periods=n_periods,
    mu=mu, sigma=sigma, LT=LT, b=b, h=h, fc=fc
)

print(f"Function returned: {result}")
print(f"First value (should be R): {result[0]}")
print(f"Second value (should be Q): {result[1]}")

# Manual EOQ calculation for comparison
omega = b/(b+h)
Q_eoq_manual = np.sqrt(2*fc*mu/h/omega)
print(f"\nExpected Q from EOQ formula: {Q_eoq_manual:.2f}")
print(f"\nInterpretation:")
if result[1] > result[0]:
    print(f"  If (R={result[0]}, Q={result[1]}): Q > R ✓ (makes sense)")
    print(f"  If (Q={result[0]}, R={result[1]}): Q < R ✗ (unusual)")
