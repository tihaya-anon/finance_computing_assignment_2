"""
检查期权套利机会

非套利条件（考虑 dividend yield q = 20%）:
1. Put-Call Parity: C - P = S*e^(-qT) - K*e^(-rT)
2. Call 边界: max(S*e^(-qT) - K*e^(-rT), 0) <= C <= S*e^(-qT)
3. Put 边界: max(K*e^(-rT) - S*e^(-qT), 0) <= P <= K*e^(-rT)

交易成本:
- 买入期权: 3.3 RMB/股 * 10000股/合约 = 33000 RMB/合约
- 卖出期权: 无成本
- A50ETF: 无成本

由于交易成本是固定的，而期权价格很小，
实际套利检验应该比较:
- 理论价格边界 vs 实际买入/卖出价格
- 如果违背幅度 > 交易成本，则有净套利空间
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
# 每股交易成本 = 3.3 RMB/股 (每张合约 10000 股)
tc_per_share = 3.3

os.makedirs("./result/q4", exist_ok=True)


def get_latest_price(df, before):
    filtered = df[df["LocalTime"] < before]
    if not filtered.empty:
        idx = filtered["LocalTime"].idxmax()
        return filtered.loc[idx, "Bid1"], filtered.loc[idx, "Ask1"]
    else:
        return None, None


def check_arbitrage(time_before):
    """检查指定时间的套利机会"""
    T = (expiry - time_before).days / 365

    # 获取标的资产价格
    equity_bid, equity_ask = get_latest_price(equity_price_df, time_before)
    if equity_bid is None or equity_ask is None:
        return None, None
    S = (equity_bid + equity_ask) / 2

    # 获取所有strike
    strikes = sorted(instruments[instruments["Type"] == "Option"]["Strike"].unique())

    results = []

    for strike in strikes:
        # 获取 Call 价格
        call_row = instruments[
            (instruments["Strike"] == strike) & (instruments["OptionType"] == "C")
        ]
        if call_row.empty:
            continue
        call_symbol = call_row["Symbol"].values[0]
        call_prices = option_price_df[option_price_df["Symbol"] == call_symbol]
        bid_call, ask_call = get_latest_price(call_prices, time_before)

        # 获取 Put 价格
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

        # 理论值
        discount_factor = np.exp(-r * T)
        dividend_discount = np.exp(-q * T)

        # Call 边界 (每股)
        call_lower = max(S * dividend_discount - strike * discount_factor, 0)
        call_upper = S * dividend_discount

        # Put 边界 (每股)
        put_lower = max(strike * discount_factor - S * dividend_discount, 0)
        put_upper = strike * discount_factor

        if bid_call is None or bid_put is None or ask_call is None or ask_put is None:
            continue
        # 无交易成本
        call_violate_no_tc = (bid_call < call_lower) or (ask_call > call_upper)
        put_violate_no_tc = (bid_put < put_lower) or (ask_put > put_upper)

        # 有交易成本 - 买入时需加上交易成本
        # 买入 Call 实际成本 = Ask + tc_per_share
        # 买入 Put 实际成本 = Ask + tc_per_share
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


# 输出结果
print("=" * 80)
print("期权套利分析")
print("=" * 80)
print(f"参数: r = {r*100}%, q = {q*100}%, 每股交易成本 = {tc_per_share} RMB")
print("=" * 80)

for minute in [31, 32, 33]:
    time_before = pd.Timestamp(f"2016-02-16 09:{minute}:00")
    df, S = check_arbitrage(time_before)

    if df is None:
        continue

    print(f"\n{'='*60}")
    print(f"时间: 09:{minute}:00, S = {S:.4f}")
    print(f"{'='*60}")

    # Call 边界违背
    call_violations_no_tc = df[df["Call_Violate_NoTC"] == True]
    call_violations_with_tc = df[df["Call_Violate_WithTC"] == True]

    print(f"\n【Call 价格边界违背】C <= S*e^(-qT)")
    print(f"  - 无交易成本: {len(call_violations_no_tc)} 个违背")
    if len(call_violations_no_tc) > 0:
        for _, row in call_violations_no_tc.iterrows():
            if row["AskCall"] > row["CallUpper"]:
                print(
                    f"    Strike {row['Strike']}: Ask={row['AskCall']:.4f} > Upper={row['CallUpper']:.4f}"
                )

    print(f"  - 有交易成本: {len(call_violations_with_tc)} 个违背")
    if len(call_violations_with_tc) > 0:
        for _, row in call_violations_with_tc.iterrows():
            if (row["AskCall"] + tc_per_share) > row["CallUpper"]:
                print(
                    f"    Strike {row['Strike']}: Ask+Cost={row['AskCall']+tc_per_share:.4f} > Upper={row['CallUpper']:.4f}"
                )

    # Put 边界违背
    put_violations_no_tc = df[df["Put_Violate_NoTC"] == True]
    put_violations_with_tc = df[df["Put_Violate_WithTC"] == True]

    print(f"\n【Put 价格边界违背】P >= K*e^(-rT) - S*e^(-qT)")
    print(f"  - 无交易成本: {len(put_violations_no_tc)} 个违背")
    if len(put_violations_no_tc) > 0:
        for _, row in put_violations_no_tc.iterrows():
            if row["BidPut"] < row["PutLower"]:
                diff = row["PutLower"] - row["BidPut"]
                print(
                    f"    Strike {row['Strike']}: Bid={row['BidPut']:.4f} < Lower={row['PutLower']:.4f} (差={diff:.4f})"
                )

    print(f"  - 有交易成本: {len(put_violations_with_tc)} 个违背")
    if len(put_violations_with_tc) > 0:
        for _, row in put_violations_with_tc.iterrows():
            if (row["BidPut"] + tc_per_share) < row["PutLower"]:
                diff = row["PutLower"] - (row["BidPut"] + tc_per_share)
                print(
                    f"    Strike {row['Strike']}: Bid+Cost={row['BidPut']+tc_per_share:.4f} < Lower={row['PutLower']:.4f}"
                )

    # 保存结果
    df.to_csv(f"./result/q4/{minute}.csv", index=False)

print("\n" + "=" * 80)
print("结论:")
print("=" * 80)
print(
    """
1. 无交易成本情况下:
   - 如果 Put 的 Bid < Lower，则存在买入套利机会：
     买入被低估的 Put，持有到期可获得无风险收益
   - 如果 Put 的 Ask > Upper，则存在卖出套利机会

2. 有交易成本情况下:
   - 买入成本 = Bid/Ask + 3.3 RMB/股
   - 套利空间必须大于交易成本才有实际利润

3. 发现的套利机会:
   - Put 边界违背（Bid < Lower）表示可以买入被低估的 Put
   - 这种违背在 OTM Put（Strike > S）中常见
"""
)
