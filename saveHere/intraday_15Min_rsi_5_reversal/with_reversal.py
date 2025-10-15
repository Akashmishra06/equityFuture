from backtestTools.util import createPortfolio, calculate_mtm, setup_logger
from backtestTools.algoLogic import baseAlgoLogic, equityOverNightAlgoLogic
from backtestTools.histData import getEquityBacktestData
from backtestTools.histData import getFnoBacktestData
from backtestTools.expiry import getExpiryData

from termcolor import colored, cprint
from datetime import datetime, time
import multiprocessing
import numpy as np
import pandas as pd
import logging
import talib

class FDRS_Single_Confermation_RSI_5(baseAlgoLogic):
    def runBacktest(self, portfolio, startDate, endDate):
        if self.strategyName != "base_withreversal":
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
            df = getFnoBacktestData(stockName, startTimeEpoch-(86400*300), endTimeEpoch, "15Min")
        except Exception as e:
            raise Exception(e)
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            print(f"❌ No data for {stockName} — skipping this process")
            return
        df['rsi'] = talib.RSI(df['c'], timeperiod=5)
        df['longEntry'] = np.where((df['rsi'] > 70), "longEntry", "")
        df['longExit'] = np.where((df['rsi'] < 30), "longExit", "")

        df['longreversal'] = np.where((df['rsi'] > 30) & (df['rsi'].shift(1) < 30), "longreversal", "")
        df['shortreversal'] = np.where((df['rsi'] < 70) & (df['rsi'].shift(1) > 70), "shortreversal", "")

        df.dropna(inplace=True)
        # df.index = df.index + 33300
        df = df[df.index > startTimeEpoch]
        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_df.csv")

        amountPerTrade = 1000000
        lastIndexTimeData = None
        DayFirstEntry = False
        secondEntry = False

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

            if lastIndexTimeData in df.index and not stockAlgoLogic.openPnl.empty:
                for index, row in stockAlgoLogic.openPnl.iterrows():
                    try:
                        # Time-based exit
                        if stockAlgoLogic.humanTime.time() >= time(15, 15):
                            exitType = f"Timeup,{row['entryType']}"
                            stockAlgoLogic.exitOrder(index, exitType, df.at[lastIndexTimeData, "c"])
                            continue  # skip further checks after time exit

                        current_close = df.at[lastIndexTimeData, "c"]

                        # ---- Long Position (Buy) Exit Conditions ----
                        if row['PositionStatus'] == 1:
                            if df.at[lastIndexTimeData, "longExit"] == "longExit":
                                exitType = f"rsiBuyExit,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                            elif row['entryType'] == "two" and df.at[lastIndexTimeData, "longExit"] == "longExit":
                                exitType = f"reversallongExit,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                            elif (row['EntryPrice'] * 0.997) > current_close:
                                exitType = f"BuyStopLoss,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                        # ---- Short Position (Sell) Exit Conditions ----
                        elif row['PositionStatus'] == -1:
                            if df.at[lastIndexTimeData, "longEntry"] == "longEntry":
                                exitType = f"rsiSellExit,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                            elif row['entryType'] == "two" and df.at[lastIndexTimeData, "longEntry"] == "longEntry":
                                exitType = f"reversalshortExit,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                            elif (row['EntryPrice'] * 1.003) < current_close:
                                exitType = f"SELLStopLoss,{row['entryType']}"
                                stockAlgoLogic.exitOrder(index, exitType, current_close)

                    except Exception as e:
                        logging.info(e)


            if DayFirstEntry == True and stockAlgoLogic.humanTime.time() >= time(15, 15):
                DayFirstEntry = False

            if DayFirstEntry == False and (not stockAlgoLogic.openPnl.empty) and (lastIndexTimeData in df.index) & (stockAlgoLogic.humanTime.time() > time(9, 30)) & (stockAlgoLogic.humanTime.time() < time(15, 15)):
                if stockName == "NIFTY 50":
                    lotSize = 75
                if (df.at[lastIndexTimeData, "longreversal"] == "longreversal") and (df.at[lastIndexTimeData, "c"] > df.at[lastIndexTimeData, "o"]):
                    entry_price = df.at[lastIndexTimeData, "c"]
                    stockAlgoLogic.entryOrder(entry_price, stockName, lotSize, "BUY", {"entryType":"two"})
                    DayFirstEntry = True

                if (df.at[lastIndexTimeData, "shortreversal"] == "shortreversal") and (df.at[lastIndexTimeData, "c"] < df.at[lastIndexTimeData, "o"]):
                    entry_price = df.at[lastIndexTimeData, "c"]
                    stockAlgoLogic.entryOrder(entry_price, stockName, lotSize, "SELL", {"entryType":"two"})
                    DayFirstEntry = True

            if (lastIndexTimeData in df.index) & (stockAlgoLogic.openPnl.empty) & (stockAlgoLogic.humanTime.time() > time(9, 30)) & (stockAlgoLogic.humanTime.time() < time(15, 15)):
                if stockName == "NIFTY 50":
                    lotSize = 75
                elif stockName == "NIFTY BANK":
                    lotSize = 30

                if (df.at[lastIndexTimeData, "longEntry"] == "longEntry") and (df.at[lastIndexTimeData, "c"] > df.at[lastIndexTimeData, "o"]):
                    entry_price = df.at[lastIndexTimeData, "c"]
                    stockAlgoLogic.entryOrder(entry_price, stockName, lotSize, "BUY", {"entryType":"one"})

                elif (df.at[lastIndexTimeData, "longExit"] == "longExit") and (df.at[lastIndexTimeData, "c"] < df.at[lastIndexTimeData, "o"]):
                    entry_price = df.at[lastIndexTimeData, "c"]
                    stockAlgoLogic.entryOrder(entry_price, stockName, lotSize, "SELL", {"entryType":"one"})

            lastIndexTimeData = timeData
            stockAlgoLogic.pnlCalculator()

        if not stockAlgoLogic.openPnl.empty:
            for index, row in stockAlgoLogic.openPnl.iterrows():
                exitType = "Time Up"
                stockAlgoLogic.exitOrder(index, exitType, (df.at[lastIndexTimeData, "c"]))
        stockAlgoLogic.pnlCalculator()


if __name__ == "__main__":
    startNow = datetime.now()

    devName = "AM"
    strategyName = "base_withreversal"
    version = "v1"

    startDate = datetime(2020, 4, 1, 9, 15)
    endDate = datetime(2025, 9, 30, 15, 30)

    portfolio = createPortfolio("/root/development/equityFuture/intraday_15Min_rsi_5_reversal/stocks.md", 1)
    # portfolio = createPortfolio("/root/development/equityFuture/intraday_15Min_rsi_5_reversal/stocksTwo.md", 1)

    algoLogicObj = FDRS_Single_Confermation_RSI_5(devName, strategyName, version)
    fileDir, closedPnl = algoLogicObj.runBacktest(portfolio, startDate, endDate)

    dailyReport = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endNow = datetime.now()
    print(f"Done. Ended in {endNow-startNow}")