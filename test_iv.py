from iv import ImpliedVolatility, BlackScholes

index, S, K, t, T, sigma, r, q = 1.1, 100, 100, 0, 1, 0.3, 0.03, 0.4
call_price = BlackScholes.call_price(S, K, t, T, sigma, r, q)
call_iv = ImpliedVolatility.call_vol(call_price, S, K, t, T, r, q)
put_price = BlackScholes.put_price(S, K, t, T, sigma, r, q)
put_iv = ImpliedVolatility.put_vol(put_price, S, K, t, T, r, q)

print(call_iv, put_iv)
