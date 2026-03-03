from iv import *
import pandas as pd
from collections import defaultdict
import csv
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

option_price_df: pd.DataFrame = ins_price_df[ins_price_df["Symbol"] != 510050]
equity_price_df: pd.DataFrame = ins_price_df[ins_price_df["Symbol"] == 510050]

expiry = pd.Timestamp("2016-02-24")
r = 0.04
q = 0.20

# Create output directory
os.makedirs("./result/q3", exist_ok=True)


def get_latest_price(df, before):
    filtered = df[df["LocalTime"] < before]
    if not filtered.empty:
        idx = filtered["LocalTime"].idxmax()
        return filtered.loc[idx, "Bid1"], filtered.loc[idx, "Ask1"]
    else:
        return None, None


def save_csv(data: dict, path: str):
    data_list = []
    for strike, vol_dict in sorted(data.items()):
        row = {"Strike": strike}
        row.update(vol_dict)
        data_list.append(row)

    if data_list:
        columns = list(data_list[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data_list)


for minute in range(31, 34):
    time_before = pd.Timestamp(f"2016-02-16 09:{minute}:00")
    T = (expiry - time_before).days / 365

    ret = {}

    # Get equity price
    equity_bid, equity_ask = get_latest_price(equity_price_df, time_before)
    if equity_bid is None or equity_ask is None:
        print(f"No equity price before {time_before}")
        continue
    equity_price = (equity_bid + equity_ask) / 2

    # Get all strikes that have options
    strikes = instruments[instruments["Type"] == "Option"]["Strike"].unique()

    for strike in strikes:
        ret[strike] = {}

        # Get Call symbol and price
        call_row = instruments[
            (instruments["Strike"] == strike) & (instruments["OptionType"] == "C")
        ]
        if not call_row.empty:
            call_symbol = call_row["Symbol"].values[0]
            call_prices = option_price_df[option_price_df["Symbol"] == call_symbol]
            bid_call, ask_call = get_latest_price(call_prices, time_before)

            if bid_call is not None and ask_call is not None:
                bid_vol_call = ImpliedVolatility.call_vol(
                    bid_call, equity_price, strike, 0, T, r, q
                )
                ask_vol_call = ImpliedVolatility.call_vol(
                    ask_call, equity_price, strike, 0, T, r, q
                )
                ret[strike]["BidVolC"] = bid_vol_call
                ret[strike]["AskVolC"] = ask_vol_call

        # Get Put symbol and price
        put_row = instruments[
            (instruments["Strike"] == strike) & (instruments["OptionType"] == "P")
        ]
        if not put_row.empty:
            put_symbol = put_row["Symbol"].values[0]
            put_prices = option_price_df[option_price_df["Symbol"] == put_symbol]
            bid_put, ask_put = get_latest_price(put_prices, time_before)

            if bid_put is not None and ask_put is not None:
                bid_vol_put = ImpliedVolatility.put_vol(
                    bid_put, equity_price, strike, 0, T, r, q
                )
                ask_vol_put = ImpliedVolatility.put_vol(
                    ask_put, equity_price, strike, 0, T, r, q
                )
                ret[strike]["BidVolP"] = bid_vol_put
                ret[strike]["AskVolP"] = ask_vol_put

    save_csv(ret, f"./result/q3/{minute}.csv")
    print(f"Saved {minute}.csv")
