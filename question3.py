from iv import *
import pandas as pd
from collections import defaultdict
import csv

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


option_price_df: pd.DataFrame = ins_price_df[ins_price_df["Symbol"] != 510050]
equity_price_df: pd.DataFrame = ins_price_df[ins_price_df["Symbol"] == 510050]
iv_09_31_00 = defaultdict(lambda: defaultdict(None))
iv_09_32_00 = defaultdict(lambda: defaultdict(None))
iv_09_33_00 = defaultdict(lambda: defaultdict(None))
time_09_30_00 = pd.Timestamp("2016-02-16 09:30:00")
time_09_31_00 = pd.Timestamp("2016-02-16 09:31:00")
time_09_32_00 = pd.Timestamp("2016-02-16 09:32:00")
time_09_33_00 = pd.Timestamp("2016-02-16 09:33:00")


def get_latest_price(df, before):
    filtered = df[df["LocalTime"] < before]
    if not filtered.empty:
        idx = filtered["LocalTime"].idxmax()  # 找最大 time 的索引
        return filtered.loc[idx, "Bid1"], filtered.loc[idx, "Ask1"]
    else:
        return None, None


def save_csv(data: defaultdict, path: str):
    data_tuple = [(k, dict(v)) for k, v in data.items()]
    data_tuple.sort(key=lambda x: x[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        columns = list(data_tuple[0][1].keys())
        columns.insert(0, "Strike")
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for strike, vol in data_tuple:
            row = vol
            row["Strike"] = strike
            writer.writerow(row)


for minute in range(31, 34):
    time_before = pd.Timestamp(f"2016-02-16 09:{minute}:00")
    ret = defaultdict(lambda: defaultdict(None))
    equity_bid, equity_ask = get_latest_price(equity_price_df, time_before)
    if equity_bid is None or equity_ask is None:
        continue
    equity_price = (equity_bid + equity_ask) / 2
    for option_symbol in option_price_df["Symbol"].unique():
        option_price = option_price_df[option_price_df["Symbol"] == option_symbol]
        option_strike_df = instruments[instruments["Symbol"] == option_symbol]
        option_call_strike = option_strike_df[option_strike_df["OptionType"] == "C"][
            "Strike"
        ].values[0]
        bid_call, ask_call = get_latest_price(
            option_price[option_price["OptionType"] == "C"], time_before
        )
        bid_vol_call, ok = ImpliedVolatility.call_vol(
            bid_call, equity_price, option_call_strike, 16 / 365, 24 / 365, 0.04, 0.20
        )
        if not ok:
            bid_vol_call = "NaN"
        ret[option_call_strike]["BidVolC"] = bid_vol_call
        ask_vol_call, ok = ImpliedVolatility.call_vol(
            ask_call, equity_price, option_call_strike, 16 / 365, 24 / 365, 0.04, 0.20
        )
        if not ok:
            ask_vol_call = "NaN"
        ret[option_call_strike]["AskVolC"] = ask_vol_call

        option_put_strike = option_strike_df[option_strike_df["OptionType"] == "P"][
            "Strike"
        ].values[0]
        bid_put, ask_put = get_latest_price(
            option_price[option_price["OptionType"] == "P"], time_before
        )
        bid_vol_put, ok = ImpliedVolatility.put_vol(
            bid_put, equity_price, option_put_strike, 16 / 365, 24 / 365, 0.04, 0.20
        )
        if not ok:
            bid_vol_put = "NaN"
        ret[option_put_strike]["BidVolC"] = bid_vol_put
        ask_vol_put, ok = ImpliedVolatility.put_vol(
            ask_put, equity_price, option_put_strike, 16 / 365, 24 / 365, 0.04, 0.20
        )
        if not ok:
            ask_vol_put = "NaN"
        ret[option_put_strike]["AskVolC"] = ask_vol_put
    save_csv(ret, f"./result/q3/{minute}.csv")
