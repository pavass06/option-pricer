"""Longstaff-Schwartz least-squares Monte Carlo (LSM) for American options.

Paths of the underlying are simulated under GBM on a grid of exercise dates.
Going backwards, the continuation value is estimated by regressing the
discounted future cash flows on a polynomial of the spot, using in-the-money
paths only (Longstaff & Schwartz, 2001). The holder exercises when the
immediate payoff exceeds this estimate.

The exercise rule is estimated, hence slightly sub-optimal: the LSM price is
biased low by a small amount, on top of the Monte Carlo noise measured by the
standard error.
"""

import math

import numpy as np

from .black_scholes import _check_kind, _check_inputs
from .monte_carlo import MCResult, Z_95


def lsm_price(S, K, T, r, sigma, kind="put", q=0.0, n_paths=100_000,
              steps=50, degree=3, antithetic=True, seed=None) -> MCResult:
    """American option price by least-squares Monte Carlo, with a 95% CI.

    steps   number of exercise dates (Longstaff-Schwartz use 50 per year)
    degree  degree of the polynomial in S/K used for the regression
    """
    kind = _check_kind(kind)
    _check_inputs(S, K, T, sigma)
    if steps < 1 or degree < 1:
        raise ValueError("steps and degree must be >= 1")
    steps = int(steps)
    rng = np.random.default_rng(seed)

    dt = T / steps
    if antithetic:
        # Odd n_paths is rounded up so that rows i and i + m are exact mirrors
        m = (n_paths + 1) // 2
        n_paths = 2 * m
        z = rng.standard_normal((m, steps))
        z = np.concatenate([z, -z])
    else:
        z = rng.standard_normal((n_paths, steps))
    increments = (r - q - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * z
    spots = S * np.exp(np.cumsum(increments, axis=1))  # columns: t_1 .. t_steps

    def payoff(s):
        return np.maximum(s - K, 0.0) if kind == "call" else np.maximum(K - s, 0.0)

    disc = math.exp(-r * dt)
    cash = payoff(spots[:, -1])  # value of each path, expressed at the current date
    for t in range(steps - 2, -1, -1):
        cash *= disc
        s_t = spots[:, t]
        exercise = payoff(s_t)
        itm = exercise > 0
        if itm.sum() > degree + 1:
            x = s_t[itm] / K  # scaled to keep the regression well conditioned
            coeffs = np.polynomial.polynomial.polyfit(x, cash[itm], degree)
            continuation = np.polynomial.polynomial.polyval(x, coeffs)
            ex_now = exercise[itm] > continuation
            idx = np.flatnonzero(itm)[ex_now]
            cash[idx] = exercise[idx]
    values = cash * disc  # back to t = 0

    # Exercise at t = 0 is allowed too (relevant only deep in the money)
    intrinsic = float(payoff(np.array([S]))[0])

    if antithetic:
        values = 0.5 * (values[:m] + values[m:])
    price = float(values.mean())
    std_error = float(values.std(ddof=1) / math.sqrt(len(values)))
    if intrinsic > price:
        return MCResult(intrinsic, 0.0, intrinsic, intrinsic, n_paths)
    return MCResult(price, std_error, price - Z_95 * std_error,
                    price + Z_95 * std_error, n_paths)
