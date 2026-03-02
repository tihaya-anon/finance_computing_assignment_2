from scipy.stats import norm
import numpy as np


def metadata(S, K, t, T, sigma, r, q):
    dt = T - t
    if dt <= 0:
        raise ValueError("T must be greater than t (positive time to maturity).")
    d_1 = (np.log(S / K) + (r - q + sigma**2 / 2) * dt) / (sigma * np.sqrt(dt))
    d_2 = d_1 - sigma * np.sqrt(dt)
    return dt, d_1, d_2


class BlackScholes:
    @classmethod
    def call_price(cls, S, K, t, T, sigma, r, q):
        dt, d_1, d_2 = metadata(S, K, t, T, sigma, r, q)
        return S * np.exp(-q * dt) * norm.cdf(d_1) - K * np.exp(-r * dt) * norm.cdf(d_2)

    @classmethod
    def put_price(cls, S, K, t, T, sigma, r, q):
        dt, d_1, d_2 = metadata(S, K, t, T, sigma, r, q)
        return K * np.exp(-r * dt) * norm.cdf(-d_2) - S * np.exp(-q * dt) * norm.cdf(
            -d_1
        )
