import pandas as pd


df = pd.read_csv("/root/development/equityFuture/FuturesAndOptions/BacktestResults/AM_intradayFuture_rsi_7_reversal_v1/2/closePnl_AM_intradayFuture_rsi_7_reversal_v1_2.csv")

df_sell = df[df['PositionStatus'] == -1]
df_buy = df[df['PositionStatus'] == 1]

df_buy.to_csv("/root/development/equityFuture/FuturesAndOptions/makeLogic/buy.csv", index=False)
df_sell.to_csv("/root/development/equityFuture/FuturesAndOptions/makeLogic/sell.csv", index=False)