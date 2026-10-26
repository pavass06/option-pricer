import math

import pytest

from option_pricer import bs_price, bs_greeks, implied_vol, mc_price, crr_price


# --- Reference values -------------------------------------------------------

def test_hull_reference_values():
    # Hull, "Options, Futures and Other Derivatives", Example 15.6:
    # S=42, K=40, r=10%, sigma=20%, T=0.5 -> call 4.76, put 0.81
    assert bs_price(42, 40, 0.5, 0.10, 0.20, "call") == pytest.approx(4.7594, abs=1e-4)
    assert bs_price(42, 40, 0.5, 0.10, 0.20, "put") == pytest.approx(0.8086, abs=1e-4)


def test_haug_reference_value():
    # Haug, "The Complete Guide to Option Pricing Formulas": call = 2.1334
    assert bs_price(60, 65, 0.25, 0.08, 0.30, "call") == pytest.approx(2.1334, abs=1e-4)


def test_american_put_longstaff_schwartz_reference():
    # Longstaff & Schwartz (2001), Table 1: S=36, K=40, r=6%, sigma=20%, T=1.
    # European put 3.844; American put 4.478 by their finite-difference grid.
    # High-resolution lattices converge to ~4.4867 (the value commonly used as
    # benchmark in later LSM papers), so we accept both within 0.01.
    am = crr_price(36, 40, 1, 0.06, 0.20, "put", steps=2000, american=True)
    assert am == pytest.approx(4.4867, abs=1e-3)
    assert am == pytest.approx(4.478, abs=1e-2)
    assert bs_price(36, 40, 1, 0.06, 0.20, "put") == pytest.approx(3.844, abs=1e-3)


# --- No-arbitrage relations ---------------------------------------------------

@pytest.mark.parametrize("S,K,T,r,sigma,q", [
    (100, 100, 1.0, 0.05, 0.20, 0.0),
    (80, 120, 0.25, 0.01, 0.45, 0.02),
    (150, 90, 3.0, 0.03, 0.10, 0.04),
])
def test_put_call_parity(S, K, T, r, sigma, q):
    c = bs_price(S, K, T, r, sigma, "call", q)
    p = bs_price(S, K, T, r, sigma, "put", q)
    assert c - p == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-10)


def test_american_put_worth_at_least_european():
    eu = crr_price(100, 110, 1, 0.05, 0.25, "put", steps=500)
    am = crr_price(100, 110, 1, 0.05, 0.25, "put", steps=500, american=True)
    assert am > eu
    assert am >= 110 - 100  # at least intrinsic value


def test_american_call_no_dividend_equals_european():
    # Without dividends early exercise of a call is never optimal
    eu = crr_price(100, 100, 1, 0.05, 0.2, "call", steps=500)
    am = crr_price(100, 100, 1, 0.05, 0.2, "call", steps=500, american=True)
    assert am == pytest.approx(eu, abs=1e-10)


# --- Greeks vs finite differences -------------------------------------------

@pytest.mark.parametrize("kind", ["call", "put"])
def test_greeks_match_finite_differences(kind):
    S, K, T, r, sigma, q = 100, 95, 0.75, 0.03, 0.25, 0.01
    g = bs_greeks(S, K, T, r, sigma, kind, q)
    h = 1e-4

    def p(**kw):
        args = dict(S=S, K=K, T=T, r=r, sigma=sigma, kind=kind, q=q)
        args.update(kw)
        return bs_price(**args)

    assert g.delta == pytest.approx((p(S=S + h) - p(S=S - h)) / (2 * h), rel=1e-6)
    assert g.gamma == pytest.approx((p(S=S + h) - 2 * p() + p(S=S - h)) / h ** 2, rel=1e-3)
    assert g.vega == pytest.approx((p(sigma=sigma + h) - p(sigma=sigma - h)) / (2 * h), rel=1e-6)
    assert g.rho == pytest.approx((p(r=r + h) - p(r=r - h)) / (2 * h), rel=1e-6)
    # theta = dV/dt = -dV/dT
    assert g.theta == pytest.approx(-(p(T=T + h) - p(T=T - h)) / (2 * h), rel=1e-6)


# --- Implied volatility -----------------------------------------------------

@pytest.mark.parametrize("K", [50, 80, 100, 120, 200])
@pytest.mark.parametrize("sigma", [0.05, 0.2, 0.8])
@pytest.mark.parametrize("kind", ["call", "put"])
def test_implied_vol_roundtrip(K, sigma, kind):
    S, T, r = 100, 0.5, 0.02
    price = bs_price(S, K, T, r, sigma, kind)
    if bs_greeks(S, K, T, r, sigma, kind).vega < 1e-6:
        # Price is (numerically) pure intrinsic value or zero: any small vol
        # reproduces it, so the inverse problem is ill-posed.
        pytest.skip("vega ~ 0: implied vol not identifiable")
    assert implied_vol(price, S, K, T, r, kind) == pytest.approx(sigma, abs=1e-5)


def test_implied_vol_rejects_arbitrage_price():
    with pytest.raises(ValueError):
        implied_vol(150.0, 100, 100, 1, 0.01, "call")  # above the spot


# --- Monte Carlo and tree convergence ---------------------------------------

@pytest.mark.parametrize("kind", ["call", "put"])
def test_mc_confidence_interval_contains_bs(kind):
    S, K, T, r, sigma = 100, 105, 1.0, 0.03, 0.2
    res = mc_price(S, K, T, r, sigma, kind, n_paths=200_000, seed=42)
    assert res.ci_low <= bs_price(S, K, T, r, sigma, kind) <= res.ci_high


@pytest.mark.parametrize("anti,cv", [(True, False), (False, True), (True, True)])
def test_variance_reduction_reduces_std_error(anti, cv):
    args = (100, 100, 1.0, 0.05, 0.2, "call")
    plain = mc_price(*args, n_paths=100_000, antithetic=False, control_variate=False, seed=1)
    reduced = mc_price(*args, n_paths=100_000, antithetic=anti, control_variate=cv, seed=1)
    # Same number of payoff evaluations, noticeably tighter interval
    assert reduced.std_error < 0.75 * plain.std_error


def test_crr_converges_to_bs():
    S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2
    bs = bs_price(S, K, T, r, sigma, "call")
    errors = [abs(crr_price(S, K, T, r, sigma, "call", steps=n) - bs) for n in (50, 200, 1000)]
    assert errors[-1] < 5e-3
    assert errors[0] > errors[-1]


# --- Input validation -------------------------------------------------------

def test_invalid_inputs():
    with pytest.raises(ValueError):
        bs_price(100, 100, 0, 0.05, 0.2)
    with pytest.raises(ValueError):
        bs_price(100, 100, 1, 0.05, 0.2, kind="straddle")
