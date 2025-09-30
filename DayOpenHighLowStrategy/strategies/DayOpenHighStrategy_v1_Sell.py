from backtestTools.algoLogic import baseAlgoLogic, equityOverNightAlgoLogic
from backtestTools.histData import getEquityBacktestData
from backtestTools.histData import getEquityHistData
from backtestTools.util import setup_logger
from datetime import datetime, time
from termcolor import colored, cprint
import multiprocessing
import pandas as pd
import numpy as np
import logging
import talib


class DayOpenHighStrategy_v1_Sell(baseAlgoLogic):

    def runBacktest(self, portfolio, startDate, endDate):

        if self.strategyName != "DayOpenHighStrategy_v1_Sell":
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
            df = getEquityBacktestData(stockName, startTimeEpoch-(7776000*5), endTimeEpoch, "5Min")
            df['datetime'] = pd.to_datetime(df['datetime'])
            df['time'] = df['datetime'].dt.strftime('%H:%M')
            df['date'] = df['datetime'].dt.date
        except Exception as e:
            raise Exception(e)
        
        try:
            df["ema5"] = talib.EMA(df["c"], timeperiod=5)
            df.dropna(inplace=True)
        except:
            self.strategyLogger.info(f"Data not found for {stockName}")
            return

        df['canTake'] = np.where(df['time'] == "09:15", "canTake", "")

        df.dropna(inplace=True)
        df['EntryTrigger1'] = np.where(((df['o'] == df['h']) & (df['canTake'] == "canTake")), "EntryTrigger1", "")


        df = df[df.index > startTimeEpoch]
        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_df.csv")

        amountPerTrade = 100000
        lastIndexTimeData = None
        stoploss = None
        entry_price = None
        Dateoftime = None

        for timeData in df.index:
            stockAlgoLogic.timeData = timeData
            stockAlgoLogic.humanTime = datetime.fromtimestamp(timeData)

            if lastIndexTimeData in df.index:
                logger.info(f"Datetime: {stockAlgoLogic.humanTime}\tStock: {stockName}\tClose: {df.at[lastIndexTimeData,'c']}")

            if not stockAlgoLogic.openPnl.empty:
                for index, row in stockAlgoLogic.openPnl.iterrows():
                    try:
                        # data = getEquityHistData(row['Symbol'], timeData)
                        stockAlgoLogic.openPnl.at[index, 'CurrentPrice'] = df.at[lastIndexTimeData, "c"]
                    except Exception as e:
                        logging.info(e)

            stockAlgoLogic.pnlCalculator()

            for index, row in stockAlgoLogic.openPnl.iterrows():
                if lastIndexTimeData in df.index:

                    if stockAlgoLogic.humanTime.time() >= time(15, 15):

                        exitType = "Time Up"
                        stockAlgoLogic.exitOrder(index, exitType)

                    elif row["PositionStatus"] == -1:

                        if df.at[lastIndexTimeData, "h"] >= (row['stoploss']):

                            exitType = "Stoploss Hit"
                            stockAlgoLogic.exitOrder(index, exitType, (row['stoploss']))


            if lastIndexTimeData is not None and (lastIndexTimeData in df.index) & (stockAlgoLogic.openPnl.empty) & (stockAlgoLogic.humanTime.time() < time(15, 15)):

                if (df.at[lastIndexTimeData, "EntryTrigger1"] == "EntryTrigger1"):


                    entry_price = df.at[lastIndexTimeData, "l"]
                    stoploss = df.at[lastIndexTimeData, "h"]

                    Dateoftime = df.at[lastIndexTimeData, "date"]
                if Dateoftime != df.at[lastIndexTimeData, "date"]:
                    entry_price = None

                if stoploss is not None and entry_price is not None and (entry_price > df.at[lastIndexTimeData, "l"]):

                    stockAlgoLogic.entryOrder(entry_price, stockName, (amountPerTrade//entry_price), "SELL", {"stoploss":stoploss})
                    entry_price = None


            lastIndexTimeData = timeData
            stockAlgoLogic.pnlCalculator()

        if not stockAlgoLogic.openPnl.empty:
            print("RuntimeError")