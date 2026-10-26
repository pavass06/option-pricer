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
from option_pricer import bs_price, bs_greeks, mc_price, crr_price  # noqa: E402

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


def greeks_figure():
    spots = np.linspace(50, 150, 201)
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4))
    panels = [("price", "Price", 1), ("delta", "Delta", 1), ("gamma", "Gamma", 1),
              ("vega", "Vega (per 1 vol point)", 100), ("theta", "Theta (per day)", 365),
              ("rho", "Rho (per 1% rate)", 100)]
    for kind, color in (("call", "#1f6feb"), ("put", "#d1495b")):
        greeks = [bs_greeks(s, K, T, r, sigma, kind) for s in spots]
        for ax, (attr, title, scale) in zip(axes.flat, panels):
            ax.plot(spots, [getattr(g, attr) / scale for g in greeks], color=color, label=kind)
    for ax, (_, title, _) in zip(axes.flat, panels):
        ax.axvline(K, color="#999999", lw=0.8, ls=":")
        ax.set_title(title)
        ax.set_xlabel("Spot")
        ax.grid(alpha=0.25)
    axes[0, 0].legend()
    fig.suptitle(f"Black-Scholes price and Greeks vs spot (K={K:.0f}, T={T:.0f}y, r={r:.0%}, "
                 f"vol={sigma:.0%}); dotted line = strike", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "greeks.png", dpi=130)
    plt.close(fig)


def monte_carlo_figure():
    bs = bs_price(S0, K, T, r, sigma, "call")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    # Left: distribution of discounted payoffs for 100,000 paths
    rng = np.random.default_rng(0)
    z = rng.standard_normal(100_000)
    s_t = S0 * np.exp((r - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * z)
    pay = np.exp(-r * T) * np.maximum(s_t - K, 0.0)
    share_zero = (pay == 0).mean()
    ax1.hist(pay[pay > 0], bins=80, color="#1f6feb", alpha=0.8)
    ax1.axvline(pay.mean(), color="black", ls="--", lw=1, label=f"Mean = {pay.mean():.4f}")
    ax1.set_xlim(0, np.quantile(pay, 0.999))
    ax1.set_xlabel("Discounted payoff of the ATM call")
    ax1.set_ylabel("Number of paths")
    ax1.set_title(f"Payoff distribution (100,000 paths; {share_zero:.0%} expire worthless, not shown)",
                  fontsize=10)
    ax1.legend(fontsize=8)

    # Right: 95% CI half-width vs number of paths, log-log
    ns = np.unique(np.logspace(3, 6, 10).astype(int))
    for label, anti, cv, color in [("Plain MC", False, False, "#9aa5b1"),
                                   ("Antithetic", True, False, "#f4a259"),
                                   ("Antithetic + control variate", True, True, "#1f6feb")]:
        hw = [1.96 * mc_price(S0, K, T, r, sigma, "call", n_paths=int(n), antithetic=anti,
                              control_variate=cv, seed=7).std_error for n in ns]
        ax2.loglog(ns, hw, "o-", ms=3, color=color, label=label)
    ax2.loglog(ns, hw[0] * np.sqrt(ns[0] / ns), color="black", lw=0.8, ls=":",
               label="slope -1/2 (error ~ 1/sqrt(N))")
    ax2.set_xlabel("Number of paths")
    ax2.set_ylabel("95% CI half-width")
    ax2.set_title(f"Confidence interval shrinks as 1/sqrt(N) (BS = {bs:.4f})", fontsize=10)
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25, which="both")

    fig.tight_layout()
    fig.savefig(OUT / "monte_carlo.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    convergence_figure()
    price_surface_figure()
    greeks_figure()
    monte_carlo_figure()
    print(f"Figures written to {OUT}")
