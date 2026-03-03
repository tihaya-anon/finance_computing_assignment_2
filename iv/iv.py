from .bs import *

EPSILON = 1e-12


class ImpliedVolatility:
    @classmethod
    def iterate(
        cls,
        option_price,
        S,
        K,
        t,
        T,
        r,
        q,
        option_price_func,
        tolerance=EPSILON,
        max_iter=100,
        max_step=0.5,
    ):
        # handle zero time-to-maturity
        dt = T - t
        if dt <= 0:
            # If at expiry, implied vol is undefined — return 0 if option price equals intrinsic, else raise
            intrinsic = (
                max(0.0, S - K)
                if option_price_func is BlackScholes.call_price
                else max(0.0, K - S)
            )
            if abs(option_price - intrinsic) < EPSILON:
                return 0.0, True
            raise ValueError("Option price inconsistent with zero time to maturity.")

        # Initial guess (Brenner-Subrahmanyam style; fallback to 0.3)
        try:
            numerator = abs(np.log(S / K) + (r - q) * dt)
            sigma_hat = np.sqrt(2 * numerator / dt) if numerator > 0 else 0.3
        except Exception:
            sigma_hat = 0.3

        sigma_hat = max(sigma_hat, EPSILON)
        for i in range(1, max_iter + 1):
            option_price_hat = option_price_func(S, K, t, T, sigma_hat, r, q)
            option_vega = cls.__vega(S, K, t, T, r, q, sigma_hat)

            # protect against tiny vega
            if option_vega < EPSILON:
                # cannot use Newton step safely; return current estimate
                return sigma_hat, True

            increment = (option_price_hat - option_price) / option_vega
            # limit step size to avoid wild jumps
            if abs(increment) > max_step:
                increment = np.sign(increment) * max_step

            sigma_new = sigma_hat - increment
            # ensure sigma stays positive and reasonable
            if sigma_new < EPSILON:
                return EPSILON, False

            if abs(sigma_new - sigma_hat) < tolerance:
                return sigma_new, True

            sigma_hat = sigma_new

        # if not converged, return last estimate (optionally raise)
        return sigma_hat, True

    @classmethod
    def __vega(cls, S, K, t, T, r, q, sigma):
        dt, d_1, _ = metadata(S, K, t, T, sigma, r, q)
        return S * np.exp(-q * dt) * norm.pdf(d_1) * np.sqrt(dt)

    @classmethod
    def call_vol(cls, option_price, S, K, t, T, r, q, tolerance=EPSILON, max_iter=100):
        return cls.iterate(
            option_price,
            S,
            K,
            t,
            T,
            r,
            q,
            BlackScholes.call_price,
            tolerance,
            max_iter,
        )

    @classmethod
    def put_vol(cls, option_price, S, K, t, T, r, q, tolerance=EPSILON, max_iter=100):
        return cls.iterate(
            option_price,
            S,
            K,
            t,
            T,
            r,
            q,
            BlackScholes.put_price,
            tolerance,
            max_iter,
        )
