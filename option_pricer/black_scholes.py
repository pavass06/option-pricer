"""Black-Scholes(-Merton) pricing and Greeks for European options.

Conventions
-----------
S      spot price
K      strike
T      time to maturity in years
r      continuously compounded risk-free rate
sigma  annualised volatility
q      continuous dividend yield (default 0)
kind   "call" or "put"

Greeks are returned per unit of the underlying parameter:
vega per 1.00 of volatility, rho per 1.00 of rate, theta per year.
Divide vega/rho by 100 and theta by 365 for the usual "desk" units.
"""

from dataclasses import dataclass
import math

from scipy.stats import norm


def _check_kind(kind: str) -> str:
    kind = kind.lower()
    if kind not in ("call", "put"):
        raise ValueError("kind must be 'call' or 'put'")
    return kind


def _check_inputs(S, K, T, sigma):
    if S <= 0 or K <= 0:
        raise ValueError("S and K must be positive")
    if T <= 0:
        raise ValueError("T must be positive")
    if sigma <= 0:
        raise ValueError("sigma must be positive")


def d1_d2(S, K, T, r, sigma, q=0.0):
    _check_inputs(S, K, T, sigma)
    vol_sqrt_t = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


def bs_price(S, K, T, r, sigma, kind="call", q=0.0):
    """Closed-form Black-Scholes price of a European option."""
    kind = _check_kind(kind)
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    df_r, df_q = math.exp(-r * T), math.exp(-q * T)
    if kind == "call":
        return float(S * df_q * norm.cdf(d1) - K * df_r * norm.cdf(d2))
    return float(K * df_r * norm.cdf(-d2) - S * df_q * norm.cdf(-d1))


@dataclass(frozen=True)
class Greeks:
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


def bs_greeks(S, K, T, r, sigma, kind="call", q=0.0) -> Greeks:
    """Price and analytical Greeks of a European option."""
    kind = _check_kind(kind)
    d1, d2 = d1_d2(S, K, T, r, sigma, q)
    sqrt_t = math.sqrt(T)
    df_r, df_q = math.exp(-r * T), math.exp(-q * T)
    pdf_d1 = float(norm.pdf(d1))

    gamma = df_q * pdf_d1 / (S * sigma * sqrt_t)
    vega = S * df_q * pdf_d1 * sqrt_t
    common_theta = -S * df_q * pdf_d1 * sigma / (2 * sqrt_t)

    if kind == "call":
        delta = df_q * norm.cdf(d1)
        theta = common_theta - r * K * df_r * norm.cdf(d2) + q * S * df_q * norm.cdf(d1)
        rho = K * T * df_r * norm.cdf(d2)
    else:
        delta = -df_q * norm.cdf(-d1)
        theta = common_theta + r * K * df_r * norm.cdf(-d2) - q * S * df_q * norm.cdf(-d1)
        rho = -K * T * df_r * norm.cdf(-d2)

    return Greeks(bs_price(S, K, T, r, sigma, kind, q), float(delta), float(gamma),
                  float(vega), float(theta), float(rho))
