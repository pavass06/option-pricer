"""Cox-Ross-Rubinstein binomial tree for European and American options."""

import math

import numpy as np

from .black_scholes import _check_kind, _check_inputs


def crr_price(S, K, T, r, sigma, kind="call", q=0.0, steps=500, american=False):
    """Price an option on a recombining CRR tree.

    With american=True the holder may exercise at every node, which matters
    for puts (and for calls when q > 0).
    """
    kind = _check_kind(kind)
    _check_inputs(S, K, T, sigma)
    if steps < 1:
        raise ValueError("steps must be >= 1")

    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    if not 0.0 < p < 1.0:
        raise ValueError("risk-neutral probability outside (0, 1): increase steps")
    disc = math.exp(-r * dt)

    def payoff(spot):
        return np.maximum(spot - K, 0.0) if kind == "call" else np.maximum(K - spot, 0.0)

    # Terminal spots: S * u^j * d^(steps - j), j = 0..steps
    j = np.arange(steps + 1)
    values = payoff(S * u ** j * d ** (steps - j))

    for n in range(steps - 1, -1, -1):
        values = disc * (p * values[1:] + (1.0 - p) * values[:-1])
        if american:
            j = np.arange(n + 1)
            values = np.maximum(values, payoff(S * u ** j * d ** (n - j)))
    return float(values[0])
