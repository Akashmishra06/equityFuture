from backtestTools.histData import getEquityBacktestData, getFnoBacktestData
from datetime import datetime
import talib
import pandas as pd

stockName = "NIFTY 50"
startDate = datetime(2025, 1, 1, 9, 15)
endDate = datetime(2025, 9, 30, 15, 29)

df = getFnoBacktestData(stockName, startDate.timestamp(), endDate.timestamp(), "D")
df['ATR'] = talib.ATR(df['h'], df['l'], df['c'], timeperiod=14)

df['prev_c'] = df['c'].shift(1)

df['date'] = pd.to_datetime(df['datetime']).dt.date
df['day_name'] = pd.to_datetime(df['datetime']).dt.day_name()
df['return_pct'] = ((df['c'] - df['prev_c']) / df['prev_c']) * 100

df['Final'] = ((df['c'] - df['prev_c']) / df['ATR']) * 100
df.index = df.index + 33300

print(df.tail())
df.dropna(inplace=True)
df.to_csv("main.csv")