"""Monte Carlo pricing of European options under geometric Brownian motion.

Only the terminal value matters for a European payoff, so S_T is sampled
exactly in one step (no time discretisation error). Two variance reduction
techniques are available:

* antithetic variates: each normal draw Z is paired with -Z;
* control variate: the discounted terminal spot, whose expectation is known
  exactly (S * exp(-q T)), is used to correct the payoff estimator.
"""

from dataclasses import dataclass
import math

import numpy as np

from .black_scholes import _check_kind, _check_inputs

Z_95 = 1.959963984540054  # two-sided 95% normal quantile


@dataclass(frozen=True)
class MCResult:
    price: float
    std_error: float
    ci_low: float
    ci_high: float
    n_paths: int

    def __str__(self):
        return (f"{self.price:.4f} +/- {1.96 * self.std_error:.4f} "
                f"(95% CI [{self.ci_low:.4f}, {self.ci_high:.4f}], n={self.n_paths})")


def mc_price(S, K, T, r, sigma, kind="call", q=0.0, n_paths=100_000,
             antithetic=True, control_variate=True, seed=None) -> MCResult:
    """Monte Carlo price with a 95% confidence interval."""
    kind = _check_kind(kind)
    _check_inputs(S, K, T, sigma)
    rng = np.random.default_rng(seed)

    if antithetic:
        # An odd n_paths is rounded up to the next even number so that every
        # draw Z has its partner -Z (pairs are rows i and i + m below).
        m = (n_paths + 1) // 2
        n_paths = 2 * m
        half = rng.standard_normal(m)
        z = np.concatenate([half, -half])
    else:
        z = rng.standard_normal(n_paths)

    drift = (r - q - 0.5 * sigma ** 2) * T
    s_t = S * np.exp(drift + sigma * math.sqrt(T) * z)
    disc = math.exp(-r * T)
    payoff = np.maximum(s_t - K, 0.0) if kind == "call" else np.maximum(K - s_t, 0.0)
    y = disc * payoff
    x = disc * s_t  # control variable: discounted S_T, E[x] = S * exp(-qT)

    if antithetic:
        # Pairs (Z, -Z) are dependent: average each pair so that the samples
        # used for the estimator and its standard error are i.i.d.
        y = 0.5 * (y[:m] + y[m:])
        x = 0.5 * (x[:m] + x[m:])

    if control_variate:
        cov = np.cov(y, x)
        if cov[1, 1] > 1e-14:  # antithetic pairs can make x almost constant
            beta = cov[0, 1] / cov[1, 1]
            y = y - beta * (x - S * math.exp(-q * T))

    samples = y
    price = float(samples.mean())
    std_error = float(samples.std(ddof=1) / math.sqrt(len(samples)))
    return MCResult(price, std_error, price - Z_95 * std_error,
                    price + Z_95 * std_error, n_paths)
