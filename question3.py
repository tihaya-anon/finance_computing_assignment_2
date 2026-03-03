from iv import *
import pandas as pd
from collections import defaultdict
import csv

instruments = pd.read_csv("./data/instruments.csv")
market_data = pd.read_csv("./data/marketdata.csv")

ins_price = pd.merge(
    market_data,
    instruments[["Symbol", "Strike", "OptionType"]],
    on="Symbol",
    how="right",
)
ins_price = ins_price[["Symbol", "Strike", "OptionType", "LocalTime", "Bid1", "Ask1"]]
ins_price["LocalTime"] = pd.to_datetime(
    ins_price["LocalTime"], format="%Y-%b-%d %H:%M:%S.%f"
)

option_price: pd.DataFrame = ins_price[ins_price["Symbol"] != 510050]
equity_price = ins_price[ins_price["Symbol"] == 510050]
iv_09_31_00 = defaultdict(lambda: defaultdict(None))
iv_09_32_00 = defaultdict(lambda: defaultdict(None))
iv_09_33_00 = defaultdict(lambda: defaultdict(None))
time_09_30_00 = pd.Timestamp("2016-02-16 09:30:00")
time_09_31_00 = pd.Timestamp("2016-02-16 09:31:00")
time_09_32_00 = pd.Timestamp("2016-02-16 09:32:00")
time_09_33_00 = pd.Timestamp("2016-02-16 09:33:00")


def get_latest_price(df: pd.DataFrame, before):
    filtered = df[df["LocalTime"] < before]
    if not filtered.empty:
        idx = filtered["LocalTime"].idxmax()  # 找最大 time 的索引
        return (filtered.loc[idx, "Bid1"] + filtered.loc[idx, "Ask1"]) / 2
    else:
        return None


equity_09_31_00 = get_latest_price(equity_price, time_09_31_00)
equity_09_32_00 = get_latest_price(equity_price, time_09_32_00)
equity_09_33_00 = get_latest_price(equity_price, time_09_33_00)

for option_price_ in option_price.itertuples(index=False):
    assert isinstance(option_price_.LocalTime, pd.Timestamp)
    local_time: pd.Timestamp = option_price_.LocalTime
    if local_time >= time_09_30_00 and local_time < time_09_31_00:
        dataset = iv_09_31_00
        equity_price_ = equity_09_31_00
    elif local_time >= time_09_31_00 and local_time < time_09_32_00:
        dataset = iv_09_32_00
        equity_price_ = equity_09_32_00
    elif local_time >= time_09_32_00 and local_time < time_09_33_00:
        dataset = iv_09_33_00
        equity_price_ = equity_09_33_00
    else:
        continue
    option_type = option_price_.OptionType
    if option_type == "C":
        bid_vol, ok = ImpliedVolatility.call_vol(
            option_price_.Bid1,
            equity_price_,
            option_price_.Strike,
            16 / 365,
            24 / 365,
            0.04,
            0.20,
        )
        if not ok:
            bid_vol = "NaN"
        ask_vol, ok = ImpliedVolatility.call_vol(
            option_price_.Ask1,
            equity_price_,
            option_price_.Strike,
            16 / 365,
            24 / 365,
            0.04,
            0.20,
        )
        if not ok:
            bid_vol = "NaN"
        dataset[option_price_.Strike]["BidVolC"] = bid_vol
        dataset[option_price_.Strike]["AskVolC"] = ask_vol
    elif option_type == "P":
        bid_vol, ok = ImpliedVolatility.put_vol(
            option_price_.Bid1,
            equity_price_,
            option_price_.Strike,
            16 / 365,
            24 / 365,
            0.04,
            0.20,
        )
        if not ok:
            bid_vol = "NaN"
        ask_vol, ok = ImpliedVolatility.put_vol(
            option_price_.Ask1,
            equity_price_,
            option_price_.Strike,
            16 / 365,
            24 / 365,
            0.04,
            0.20,
        )
        if not ok:
            bid_vol = "NaN"
        dataset[option_price_.Strike]["BidVolP"] = bid_vol
        dataset[option_price_.Strike]["AskVolP"] = ask_vol


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


save_csv(iv_09_31_00, "./result/q3/31.csv")
save_csv(iv_09_32_00, "./result/q3/32.csv")
save_csv(iv_09_33_00, "./result/q3/33.csv")
