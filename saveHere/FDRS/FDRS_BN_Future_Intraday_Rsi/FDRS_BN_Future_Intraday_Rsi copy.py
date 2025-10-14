from backtestTools.util import createPortfolio, calculate_mtm, setup_logger
from backtestTools.algoLogic import baseAlgoLogic, equityOverNightAlgoLogic
# from backtestTools.histData import getEquityBacktestData
from backtestTools.histData import getFnoBacktestData

from termcolor import colored, cprint
from datetime import datetime, time
import multiprocessing
import pandas as pd
import numpy as np
import logging
import talib


class FDRS_BN_Future_Intraday_Rsi(baseAlgoLogic):
    def runBacktest(self, portfolio, startDate, endDate):
        if self.strategyName != "FDRS_BN_Future_Intraday_Rsi":
            raise Exception("Strategy Name Mismatch")
        total_backtests = sum(len(batch) for batch in portfolio)
        completed_backtests = 0
        cprint(f"Backtesting: {self.strategyName} UID: {self.fileDirUid}", "green")
        print(colored("Backtesting 0% complete.", "light_yellow"), end="\r")
        for batch in portfolio:
            processes = []
            for stock in batch:
                p = multiprocessing.Process(target=self.backtest, args=(stock, startDate, endDate))
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
                completed_backtests += 1
                percent_done = (completed_backtests / total_backtests) * 100
                print(colored(f"Backtesting {percent_done:.2f}% complete.", "light_yellow"), end=("\r" if percent_done != 100 else "\n"))
        return self.fileDir["backtestResultsStrategyUid"], self.combinePnlCsv()

    def backtest(self, stockName, startDate, endDate):

        startTimeEpoch = startDate.timestamp()
        endTimeEpoch = endDate.timestamp()

        stockAlgoLogic = equityOverNightAlgoLogic(stockName, self.fileDir)

        logger = setup_logger(stockName, f"{self.fileDir['backtestResultsStrategyLogs']}/{stockName}.log",)
        logger.propagate = False

        try:
            df = getFnoBacktestData(stockName, startTimeEpoch-(86400*300), endTimeEpoch, "1Min")
            df_1H = getFnoBacktestData(stockName, startTimeEpoch-(86400*300), endTimeEpoch, "1H")
        except Exception as e:
            raise Exception(e)


        import pandas as pd

        # Ensure datetime columns are in datetime format
        df['datetime'] = pd.to_datetime(df['datetime'])
        df_1H['datetime'] = pd.to_datetime(df_1H['datetime'])

        # Merge df with df_1H on datetime, renaming df_1H's 'c' column to 'c_y' before merge
        df = df.merge(df_1H[['datetime', 'c']].rename(columns={'c': 'c_y'}),
                      on='datetime', how='left')

        df.to_csv("main.csv")
        # Reset index
        # df.reset_index(drop=True, inplace=True)



        # print("✅ Merge complete! Final shape:", df.shape)
        # df['rsi'] = talib.RSI(df['c'], timeperiod=14)
        # df['prev_rsi'] = df['rsi'].shift(1)

        # df['longEntry'] = np.where((df['rsi'] > 70) & (df['c'] >= df['o']), "longEntry", "")
        # df['longExit'] = np.where((df['rsi'] < 30) & (df['c'] < df['o']), "longExit", "")

        print(df)
        # # df.dropna(inplace=True)
        # df = df[df.index > startTimeEpoch]
        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_df.csv")


if __name__ == "__main__":
    startNow = datetime.now()

    devName = "NA"
    strategyName = "FDRS_BN_Future_Intraday_Rsi"
    version = "v1"

    startDate = datetime(2025, 8, 1, 9, 15)
    endDate = datetime(2025, 9, 30, 15, 30)

    portfolio = createPortfolio("/root/akashEquityBacktestAlgos/FDRS/stocks.md", 1)

    algoLogicObj = FDRS_BN_Future_Intraday_Rsi(devName, strategyName, version)
    fileDir, closedPnl = algoLogicObj.runBacktest(portfolio, startDate, endDate)

    dailyReport = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endNow = datetime.now()
    print(f"Done. Ended in {endNow-startNow}")