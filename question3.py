from iv import *
import pandas as pd
instruments = pd.read_csv("./data/instruments.csv")
market_data = pd.read_csv("./data/marketdata.csv")

print(instruments)