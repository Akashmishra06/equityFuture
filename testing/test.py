from backtestTools.histData import getEquityBacktestData
from datetime import datetime, time


symbol = ['HDFCBANK', 'RELIANCE', 'ABB', 'ACC']
startDate = datetime(2024, 1, 1, 9, 15)
endDate = datetime(2025, 9, 30, 15, 29)

startDateTimeEpoch = startDate.timestamp()
endDateTimeEpoch = endDate.timestamp()

timeFrame = "1Min"

for stock in symbol:
    df = getEquityBacktestData(stock, startDateTimeEpoch, endDateTimeEpoch, "D")

    print(df)