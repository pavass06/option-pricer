"""Minimal tour of the package. Run from the project root: python examples/quickstart.py"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from option_pricer import bs_price, bs_greeks, implied_vol, mc_price, crr_price  # noqa: E402

S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20

g = bs_greeks(S, K, T, r, sigma, "call")
print(f"BS call            : {g.price:.4f}")
print(f"  delta {g.delta:.4f} | gamma {g.gamma:.4f} | vega {g.vega / 100:.4f} per vol pt"
      f" | theta {g.theta / 365:.4f} per day | rho {g.rho / 100:.4f} per rate pt")
print(f"Implied vol of 10.4506 : {implied_vol(10.4506, S, K, T, r, 'call'):.4%}")
print(f"MC call (antithetic + CV): {mc_price(S, K, T, r, sigma, 'call', n_paths=100_000, seed=0)}")
print(f"European put (BS)  : {bs_price(S, K, T, r, sigma, 'put'):.4f}")
print(f"American put (CRR, 1000 steps): {crr_price(S, K, T, r, sigma, 'put', steps=1000, american=True):.4f}")
