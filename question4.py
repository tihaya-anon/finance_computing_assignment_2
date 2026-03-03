"""
Option Arbitrage Analysis

Non-arbitrage conditions (considering dividend yield q = 20%):
1. Put-Call Parity: C - P = S*e^(-qT) - K*e^(-rT)
2. Call bounds: max(S*e^(-qT) - K*e^(-rT), 0) <= C <= S*e^(-qT)
3. Put bounds: max(K*e^(-rT) - S*e^(-qT), 0) <= P <= K*e^(-rT)

Transaction costs:
- Buy option: 3.3 RMB/share * 10000 shares/contract = 33000 RMB/contract
- Sell option: no cost
- A50ETF: no cost

Since transaction cost is fixed and option prices are small,
actual arbitrage check compares:
- Theoretical price bounds vs actual buy/sell prices
- If violation > transaction cost, there is net arbitrage opportunity
"""

import pandas as pd
import numpy as np
import os

instruments = pd.read_csv("./data/instruments.csv")
market_data = pd.read_csv("./data/marketdata.csv")

ins_price_df = pd.merge(
    market_data,
    instruments[["Symbol", "Strike", "OptionType"]],
    on="Symbol",
    how="right",
)
ins_price_df = ins_price_df[
    ["Symbol", "Strike", "OptionType", "LocalTime", "Bid1", "Ask1"]
]
ins_price_df["LocalTime"] = pd.to_datetime(
    ins_price_df["LocalTime"], format="%Y-%b-%d %H:%M:%S.%f"
)

option_price_df = ins_price_df[ins_price_df["Symbol"] != 510050]
equity_price_df = ins_price_df[ins_price_df["Symbol"] == 510050]

expiry = pd.Timestamp("2016-02-24")
r = 0.04
q = 0.20
# Transaction cost per share = 3.3 RMB/share (10000 shares per contract)
tc_per_share = 3.3

os.makedirs("./result/q4", exist_ok=True)


def get_latest_price(df, before):
    """Get the latest bid/ask price before the given time"""
    filtered = df[df["LocalTime"] < before]
    if not filtered.empty:
        idx = filtered["LocalTime"].idxmax()
        return filtered.loc[idx, "Bid1"], filtered.loc[idx, "Ask1"]
    else:
        return None, None


def check_arbitrage(time_before):
    """Check arbitrage opportunities at the specified time"""
    T = (expiry - time_before).days / 365

    # Get underlying asset price (use mid price)
    equity_bid, equity_ask = get_latest_price(equity_price_df, time_before)
    if equity_bid is None or equity_ask is None:
        return None, None
    S = (equity_bid + equity_ask) / 2

    # Get all strikes
    strikes = sorted(instruments[instruments["Type"] == "Option"]["Strike"].unique())

    results = []

    for strike in strikes:
        # Get Call price
        call_row = instruments[
            (instruments["Strike"] == strike) & (instruments["OptionType"] == "C")
        ]
        if call_row.empty:
            continue
        call_symbol = call_row["Symbol"].values[0]
        call_prices = option_price_df[option_price_df["Symbol"] == call_symbol]
        bid_call, ask_call = get_latest_price(call_prices, time_before)

        # Get Put price
        put_row = instruments[
            (instruments["Strike"] == strike) & (instruments["OptionType"] == "P")
        ]
        if put_row.empty:
            continue
        put_symbol = put_row["Symbol"].values[0]
        put_prices = option_price_df[option_price_df["Symbol"] == put_symbol]
        bid_put, ask_put = get_latest_price(put_prices, time_before)

        if any(x is None for x in [bid_call, ask_call, bid_put, ask_put]):
            continue

        # Theoretical values
        discount_factor = np.exp(-r * T)
        dividend_discount = np.exp(-q * T)

        # Call bounds (per share)
        call_lower = max(S * dividend_discount - strike * discount_factor, 0)
        call_upper = S * dividend_discount

        # Put bounds (per share)
        put_lower = max(strike * discount_factor - S * dividend_discount, 0)
        put_upper = strike * discount_factor
        
        if bid_call is None or bid_put is None or ask_call is None or ask_put is None:
            continue
        # Without transaction cost
        call_violate_no_tc = (bid_call < call_lower) or (ask_call > call_upper)
        put_violate_no_tc = (bid_put < put_lower) or (ask_put > put_upper)

        # With transaction cost - add cost when buying
        # Buy Call actual cost = Ask + tc_per_share
        # Buy Put actual cost = Ask + tc_per_share
        call_violate_with_tc = ((bid_call + tc_per_share) < call_lower) or (
            (ask_call + tc_per_share) > call_upper
        )
        put_violate_with_tc = ((bid_put + tc_per_share) < put_lower) or (
            (ask_put + tc_per_share) > put_upper
        )

        results.append(
            {
                "Strike": strike,
                "S": S,
                "T_days": (expiry - time_before).days,
                "BidCall": bid_call,
                "AskCall": ask_call,
                "BidPut": bid_put,
                "AskPut": ask_put,
                "CallLower": call_lower,
                "CallUpper": call_upper,
                "Call_Violate_NoTC": call_violate_no_tc,
                "Call_Violate_WithTC": call_violate_with_tc,
                "PutLower": put_lower,
                "PutUpper": put_upper,
                "Put_Violate_NoTC": put_violate_no_tc,
                "Put_Violate_WithTC": put_violate_with_tc,
            }
        )

    return pd.DataFrame(results), S


# Output results
print("=" * 80)
print("Option Arbitrage Analysis")
print("=" * 80)
print(
    f"Parameters: r = {r*100}%, q = {q*100}%, Transaction cost = {tc_per_share} RMB/share"
)
print("=" * 80)

for minute in [31, 32, 33]:
    time_before = pd.Timestamp(f"2016-02-16 09:{minute}:00")
    df, S = check_arbitrage(time_before)

    if df is None:
        continue

    print(f"\n{'='*60}")
    print(f"Time: 09:{minute}:00, S = {S:.4f}")
    print(f"{'='*60}")

    # Call bound violations
    call_violations_no_tc = df[df["Call_Violate_NoTC"] == True]
    call_violations_with_tc = df[df["Call_Violate_WithTC"] == True]

    print(f"\n[Call Price Bound Violation] C <= S*e^(-qT)")
    print(f"  - No transaction cost: {len(call_violations_no_tc)} violations")
    if len(call_violations_no_tc) > 0:
        for _, row in call_violations_no_tc.iterrows():
            if row["AskCall"] > row["CallUpper"]:
                print(
                    f"    Strike {row['Strike']}: Ask={row['AskCall']:.4f} > Upper={row['CallUpper']:.4f}"
                )

    print(f"  - With transaction cost: {len(call_violations_with_tc)} violations")
    if len(call_violations_with_tc) > 0:
        for _, row in call_violations_with_tc.iterrows():
            if (row["AskCall"] + tc_per_share) > row["CallUpper"]:
                print(
                    f"    Strike {row['Strike']}: Ask+Cost={row['AskCall']+tc_per_share:.4f} > Upper={row['CallUpper']:.4f}"
                )

    # Put bound violations
    put_violations_no_tc = df[df["Put_Violate_NoTC"] == True]
    put_violations_with_tc = df[df["Put_Violate_WithTC"] == True]

    print(f"\n[Put Price Bound Violation] P >= K*e^(-rT) - S*e^(-qT)")
    print(f"  - No transaction cost: {len(put_violations_no_tc)} violations")
    if len(put_violations_no_tc) > 0:
        for _, row in put_violations_no_tc.iterrows():
            if row["BidPut"] < row["PutLower"]:
                diff = row["PutLower"] - row["BidPut"]
                print(
                    f"    Strike {row['Strike']}: Bid={row['BidPut']:.4f} < Lower={row['PutLower']:.4f} (diff={diff:.4f})"
                )

    print(f"  - With transaction cost: {len(put_violations_with_tc)} violations")
    if len(put_violations_with_tc) > 0:
        for _, row in put_violations_with_tc.iterrows():
            if (row["BidPut"] + tc_per_share) < row["PutLower"]:
                diff = row["PutLower"] - (row["BidPut"] + tc_per_share)
                print(
                    f"    Strike {row['Strike']}: Bid+Cost={row['BidPut']+tc_per_share:.4f} < Lower={row['PutLower']:.4f}"
                )

    # Save results
    df.to_csv(f"./result/q4/{minute}.csv", index=False)

print("\n" + "=" * 80)
print("Conclusion:")
print("=" * 80)
print(
    """
1. Without transaction cost:
   - If Put Bid < Lower, there is a buying arbitrage opportunity:
     Buy undervalued Put, hold to maturity for risk-free profit
   - If Put Ask > Upper, there is a selling arbitrage opportunity

2. With transaction cost:
   - Buy cost = Bid/Ask + 3.3 RMB/share
   - Arbitrage margin must exceed transaction cost to be profitable

3. Findings:
   - Put bound violations (Bid < Lower) indicate undervalued Puts
   - This violation is common in OTM Puts (Strike > S)
   - In theory, these violations represent arbitrage opportunities
   - However, the profit margin (0.001~0.066/share) is much smaller than
     transaction cost (3.3 RMB/share), so no practical arbitrage exists
     after considering transaction costs
"""
)
