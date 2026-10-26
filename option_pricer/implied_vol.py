"""Implied volatility: Newton-Raphson on vega, with a bisection fallback."""

import math

from .black_scholes import bs_price, bs_greeks, _check_kind


def _no_arbitrage_bounds(S, K, T, r, kind, q):
    df_r, df_q = math.exp(-r * T), math.exp(-q * T)
    if kind == "call":
        return max(S * df_q - K * df_r, 0.0), S * df_q
    return max(K * df_r - S * df_q, 0.0), K * df_r


def implied_vol(price, S, K, T, r, kind="call", q=0.0,
                tol=1e-8, max_iter=100, sigma_low=1e-6, sigma_high=5.0):
    """Return the Black-Scholes volatility that reproduces `price`.

    Newton steps are tried first (fast near the money). If a step leaves the
    bracket [sigma_low, sigma_high] or vega is too small (deep ITM/OTM, short
    maturities), the solver switches to bisection, which always converges.
    """
    kind = _check_kind(kind)
    lower, upper = _no_arbitrage_bounds(S, K, T, r, kind, q)
    if not (lower - 1e-12 <= price <= upper + 1e-12):
        raise ValueError(
            f"price {price:.6f} outside no-arbitrage bounds [{lower:.6f}, {upper:.6f}]")

    def f(sig):
        return bs_price(S, K, T, r, sig, kind, q) - price

    lo, hi = sigma_low, sigma_high
    if f(lo) > 0 or f(hi) < 0:
        raise ValueError("implied vol outside the search interval")

    # Newton-Raphson, keeping a valid bracket as we go
    sigma = 0.2
    for _ in range(max_iter):
        diff = f(sigma)
        if abs(diff) < tol:
            return sigma
        if diff > 0:
            hi = sigma
        else:
            lo = sigma
        vega = bs_greeks(S, K, T, r, sigma, kind, q).vega
        if vega < 1e-10:
            break
        new_sigma = sigma - diff / vega
        if not (lo < new_sigma < hi):
            break
        sigma = new_sigma

    # Bisection fallback on the remaining bracket
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        diff = f(mid)
        if abs(diff) < tol or (hi - lo) < 1e-12:
            return mid
        if diff > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)
