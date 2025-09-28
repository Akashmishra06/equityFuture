from backtestTools.algoLogic import baseAlgoLogic, equityOverNightAlgoLogic
from backtestTools.util import createPortfolio, calculate_mtm
from backtestTools.histData import getEquityBacktestData
from backtestTools.util import setup_logger

from termcolor import colored, cprint
from datetime import datetime
import multiprocessing
import numpy as np
import logging
import talib


class EquityFuture(baseAlgoLogic):
    def runBacktest(self, portfolio, startDate, endDate):
        if self.strategyName != "spotFutureBuyOnly_40_with_trailing":
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
            df = getEquityBacktestData(stockName, startTimeEpoch-(84400*1000), endTimeEpoch, "D")
        except Exception as e:
            raise Exception(e)

        df['rsi'] = talib.RSI(df['c'], timeperiod=14)
        df['prev_rsi'] = df['rsi'].shift(1)
        df['ema_10'] = talib.EMA(df['c'], timeperiod=10)
        df['LongBuy'] = np.where((df['rsi'] > 40) & (df['prev_rsi'] <= 40) & (df['ema_10'] > df['ema_10'].shift(1)), "LongBuy", "")
        df['shortSell'] = np.where((df['rsi'] < 40) & (df['prev_rsi'] >= 40), "shortSell", "")

        df.dropna(inplace=True)
        df.index = df.index + 33300
        df = df[df.index > startTimeEpoch]
        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_df.csv")

        amountPerTrade = 10000000
        lastIndexTimeData = None
        TrailingTrigger = False

        for timeData in df.index:
            stockAlgoLogic.timeData = timeData
            stockAlgoLogic.humanTime = datetime.fromtimestamp(timeData)

            if lastIndexTimeData in df.index:
                logger.info(f"Datetime: {stockAlgoLogic.humanTime}\tStock: {stockName}\tClose: {df.at[lastIndexTimeData,'c']}")

            if not stockAlgoLogic.openPnl.empty:
                for index, row in stockAlgoLogic.openPnl.iterrows():
                    try:
                        stockAlgoLogic.openPnl.at[index, 'CurrentPrice'] = df.at[lastIndexTimeData, "c"]
                    except Exception as e:
                        logging.info(e)

            stockAlgoLogic.pnlCalculator()

            if (lastIndexTimeData in df.index) and df.at[lastIndexTimeData, "rsi"] > 70:
                TrailingTrigger = True

            for index, row in stockAlgoLogic.openPnl.iterrows():
                if lastIndexTimeData in df.index:

                    if row['PositionStatus'] == 1:

                        if (df.at[lastIndexTimeData, "shortSell"] == "shortSell"):
                            exitType = "BUYEXIT"
                            stockAlgoLogic.exitOrder(index, exitType, (df.at[lastIndexTimeData, "c"]))

                        elif TrailingTrigger and df.at[lastIndexTimeData, "rsi"] < 50 and row['EntryPrice'] < row['CurrentPrice']:
                            exitType = "TrailingStoploss"
                            stockAlgoLogic.exitOrder(index, exitType, (df.at[lastIndexTimeData, "c"]))

            if (lastIndexTimeData in df.index) & (stockAlgoLogic.openPnl.empty):

                if (df.at[lastIndexTimeData, "LongBuy"] == "LongBuy"):
                    entry_price = df.at[lastIndexTimeData, "c"]
                    stockAlgoLogic.entryOrder(entry_price, stockName, (amountPerTrade//entry_price), "BUY")
                    TrailingTrigger = False

            lastIndexTimeData = timeData
            stockAlgoLogic.pnlCalculator()

        if not stockAlgoLogic.openPnl.empty:
            for index, row in stockAlgoLogic.openPnl.iterrows():
                exitType = "Time Up"
                stockAlgoLogic.exitOrder(index, exitType, (df.at[lastIndexTimeData, "c"]))
        stockAlgoLogic.pnlCalculator()


if __name__ == "__main__":
    startNow = datetime.now()

    devName = "NA"
    strategyName = "spotFutureBuyOnly_40_with_trailing"
    version = "v1"

    startDate = datetime(2020, 4, 1, 9, 15)
    endDate = datetime(2025, 9, 20, 15, 30)

    portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/Fno_173.md", 5)
    # portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/test1.md",1)
    # portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/nifty50.md",2)

    algoLogicObj = EquityFuture(devName, strategyName, version)
    fileDir, closedPnl = algoLogicObj.runBacktest(portfolio, startDate, endDate)

    dailyReport = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endNow = datetime.now()
    print(f"Done. Ended in {endNow-startNow}")