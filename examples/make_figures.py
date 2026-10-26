"""Generate the README figures in docs/.

Run from the project root:  python examples/make_figures.py
"""

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from option_pricer import bs_price, mc_price, crr_price  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs"
OUT.mkdir(exist_ok=True)

S0, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20


def convergence_figure():
    bs = bs_price(S0, K, T, r, sigma, "call")
    ns = np.unique(np.logspace(2.5, 5.5, 13).astype(int))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    for label, anti, cv, color in [("Plain MC", False, False, "#9aa5b1"),
                                   ("Antithetic + control variate", True, True, "#1f6feb")]:
        res = [mc_price(S0, K, T, r, sigma, "call", n_paths=n, antithetic=anti,
                        control_variate=cv, seed=int(n)) for n in ns]
        price = np.array([x.price for x in res])
        ax1.fill_between(ns, [x.ci_low for x in res], [x.ci_high for x in res],
                         color=color, alpha=0.25)
        ax1.plot(ns, price, "o-", color=color, ms=3, label=f"{label} (95% CI)")
    ax1.axhline(bs, color="black", lw=1, ls="--", label=f"Black-Scholes = {bs:.4f}")
    ax1.set_xscale("log")
    ax1.set_xlabel("Number of paths")
    ax1.set_ylabel("ATM call price")
    ax1.set_title("Monte Carlo convergence")
    ax1.legend(fontsize=8)

    steps = np.arange(10, 401, 5)
    err = [crr_price(S0, K, T, r, sigma, "call", steps=int(n)) - bs for n in steps]
    ax2.plot(steps, err, color="#d1495b", lw=1)
    ax2.axhline(0, color="black", lw=1, ls="--")
    ax2.set_xlabel("Tree steps")
    ax2.set_ylabel("CRR price - BS price")
    ax2.set_title("Binomial tree (CRR) error, European call")

    fig.tight_layout()
    fig.savefig(OUT / "convergence.png", dpi=130)
    plt.close(fig)


def price_surface_figure():
    spots = np.linspace(60, 140, 41)
    mats = np.linspace(0.05, 2.0, 40)
    Sg, Tg = np.meshgrid(spots, mats)
    euro = np.vectorize(lambda s, t: bs_price(s, K, t, r, sigma, "put"))(Sg, Tg)

    fig = plt.figure(figsize=(11, 4.4))
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    ax.plot_surface(Sg, Tg, euro, cmap="viridis", linewidth=0, antialiased=True)
    ax.set_xlabel("Spot")
    ax.set_ylabel("Maturity (y)")
    ax.set_zlabel("Price")
    ax.set_title("European put price (Black-Scholes)")

    ax2 = fig.add_subplot(1, 2, 2)
    am = [crr_price(s, K, 1.0, r, sigma, "put", steps=300, american=True) for s in spots]
    eu = [bs_price(s, K, 1.0, r, sigma, "put") for s in spots]
    ax2.plot(spots, am, color="#d1495b", label="American put (CRR, 300 steps)")
    ax2.plot(spots, eu, color="#1f6feb", label="European put (BS)")
    ax2.plot(spots, np.maximum(K - spots, 0), color="black", lw=1, ls="--", label="Payoff")
    ax2.set_xlabel("Spot")
    ax2.set_ylabel("Price")
    ax2.set_title("Early exercise premium, T = 1y")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT / "price_surface.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    convergence_figure()
    price_surface_figure()
    print(f"Figures written to {OUT}")
