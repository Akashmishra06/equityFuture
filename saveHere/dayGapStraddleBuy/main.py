from backtestTools.histData import getEquityBacktestData, getFnoBacktestData
from datetime import datetime
import talib
import pandas as pd

stockName = "NIFTY 50"
startDate = datetime(2020, 1, 1, 9, 15)
endDate = datetime(2025, 10, 13, 15, 29)

df = getFnoBacktestData(stockName, startDate.timestamp(), endDate.timestamp(), "D")
df['ATR'] = talib.ATR(df['h'], df['l'], df['c'], timeperiod=14)
df['prev_atr'] = df['ATR'].shift(1)
df['prev_c'] = df['c'].shift(1)
df['date'] = pd.to_datetime(df['datetime']).dt.date
df['day_name'] = pd.to_datetime(df['datetime']).dt.day_name()
df['return_pct'] = ((df['o'] - df['prev_c']) / df['prev_c']) * 100
df['Final'] = ((df['o'] - df['prev_c']) / df['prev_atr']) * 100
df.index = df.index + 33300
df.dropna(inplace=True)

df['Final'] = abs(df['Final'].round(0).astype(int))
df['prev_atr'] = df['prev_atr'].round(0).astype(int)

pivot_df = df.pivot(index='date', columns='day_name', values='Final')
pivot_df['ATR'] = df.groupby('date')['prev_atr'].first()
pivot_df.to_excel("main.xlsx", index=True)
df.to_csv("main.csv", index=False)
