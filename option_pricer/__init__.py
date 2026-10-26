"""option_pricer: small, tested toolkit for vanilla option pricing."""

from .black_scholes import bs_price, bs_greeks, Greeks
from .implied_vol import implied_vol
from .monte_carlo import mc_price, MCResult
from .binomial import crr_price
from .lsm import lsm_price

__all__ = ["bs_price", "bs_greeks", "Greeks", "implied_vol",
           "mc_price", "MCResult", "crr_price", "lsm_price"]
__version__ = "0.2.0"
