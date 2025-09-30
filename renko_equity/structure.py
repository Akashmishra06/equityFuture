from backtestTools.algoLogic import baseAlgoLogic, equityOverNightAlgoLogic
from backtestTools.util import createPortfolio, calculate_mtm, setup_logger
from backtestTools.histData import getEquityBacktestData
import indicators as indicators

from termcolor import colored, cprint
from datetime import datetime, time
import numpy as np
import logging
import talib
import pandas as pd


class EquityFuture(baseAlgoLogic):
    def runBacktest(self, portfolio, startDate, endDate):
        if self.strategyName != "spotFutureBuyOnly_40":
            raise Exception("Strategy Name Mismatch")

        total_backtests = sum(len(batch) for batch in portfolio)
        completed_backtests = 0
        cprint(f"Backtesting: {self.strategyName} UID: {self.fileDirUid}", "green")
        print(colored("Backtesting 0% complete.", "light_yellow"), end="\r")

        for batch in portfolio:
            for stock in batch:
                self.backtest(stock, startDate, endDate)
                completed_backtests += 1
                percent_done = (completed_backtests / total_backtests) * 100
                print(colored(f"Backtesting {percent_done:.2f}% complete.", "light_yellow"),
                      end=("\r" if percent_done != 100 else "\n"))

        return self.fileDir["backtestResultsStrategyUid"], self.combinePnlCsv()

    def backtest(self, stockName, startDate, endDate):
        startTimeEpoch = startDate.timestamp()
        endTimeEpoch = endDate.timestamp()

        stockAlgoLogic = equityOverNightAlgoLogic(stockName, self.fileDir)

        logger = setup_logger(stockName, f"{self.fileDir['backtestResultsStrategyLogs']}/{stockName}.log")
        logger.propagate = False

        try:
            df = getEquityBacktestData(stockName, startTimeEpoch - (84400 * 1000), endTimeEpoch, "D")
        except Exception as e:
            raise Exception(e)

        # Renko helper
        def getRenkoData(df, renkoSize):
            df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "datetime": "date"})
            renko = indicators.Renko(df)
            renko.brick_size = renkoSize
            renko.chart_type = indicators.Renko.PERIOD_CLOSE
            renkoData = renko.get_ohlc_data()
            renkoData = renkoData.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "date": "datetime"})
            renkoData["datetime2"] = renkoData["datetime"]
            renkoData.set_index("datetime2", inplace=True)
            renkoData = renkoData.reset_index().set_index("datetime2").sort_index()
            renkoData.index = (renkoData.index.values.astype(np.int64) // 10**9) - 19800
            renkoData.insert(loc=0, column="ti", value=renkoData.index)
            renkoData['signal'] = np.where(renkoData['uptrend'] == True, 1, -1)
            return renkoData

        # RSI signals
        df['rsi'] = talib.RSI(df['c'], timeperiod=14)
        df['prev_rsi'] = df['rsi'].shift(1)
        df['LongBuy'] = np.where((df['rsi'] > 40) & (df['prev_rsi'] <= 40), "LongBuy", "")
        df['shortSell'] = np.where((df['rsi'] < 40) & (df['prev_rsi'] >= 40), "shortSell", "")

        df.dropna(inplace=True)
        df.index = df.index + 33300
        df = df[df.index > startTimeEpoch]
        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_df.csv")

        current_day = None
        lastIndexTimeData = [0, 0]
        lastIndexTimeData_r = [0, 0]
        df_renko = None

        for timeData in df.index:
            stockAlgoLogic.timeData = timeData
            stockAlgoLogic.humanTime = datetime.fromtimestamp(timeData)
            new_day = stockAlgoLogic.humanTime.date()

            if current_day != new_day:
                current_day = new_day
                day_close = df.iloc[0]['c']
                renkoSize = round(day_close * 0.01)
                stockAlgoLogic.strategyLogger.info(f"Datetime:{stockAlgoLogic.humanTime}\tRenkoSize:{renkoSize}\tDayClose:{day_close}")
                df_renko = getRenkoData(df, renkoSize)
                df_renko.to_csv(f"{self.fileDir['backtestResultsCandleData']}{stockName}_Renko_{current_day}.csv")

            # Update lastIndexTimeData
            lastIndexTimeData.pop(0)
            lastIndexTimeData.append(timeData - 60)

            lastIndexTimeData_r.pop(0)
            lastIndexTimeData_r.append(timeData - 60)

            if lastIndexTimeData_r[1] in df_renko.index:
                current_renko = df_renko.at[lastIndexTimeData_r[1], 'signal']
            # current_renko_value = current_renko.iloc[0] if isinstance(current_renko, pd.Series) else current_renko

            if not stockAlgoLogic.openPnl.empty:
                for index, row in stockAlgoLogic.openPnl.iterrows():
                    try:
                        stockAlgoLogic.openPnl.at[index, 'CurrentPrice'] = df.at[lastIndexTimeData[1], "c"]
                    except Exception as e:
                        logging.info(e)

            stockAlgoLogic.pnlCalculator()

            for index, row in stockAlgoLogic.openPnl.iterrows():
                if lastIndexTimeData[1] in df.index:

                    if stockAlgoLogic.humanTime.time() >= time(15, 15):
                        exitType = "timeUp"
                        stockAlgoLogic.exitOrder(index, exitType)

            if (lastIndexTimeData[1] in df.index) & (lastIndexTimeData_r[1] in df.index)  & (stockAlgoLogic.openPnl.empty):
                
                if df.at[lastIndexTimeData_r[1], "c"] > df.at[lastIndexTimeData_r[1], "o"]:
                    entryPrice = df.at[lastIndexTimeData[1], "c"]
                    stockAlgoLogic.entryOrder(entryPrice, stockName, 100000//entryPrice, "BUY")
                
                elif df.at[lastIndexTimeData_r[1], "c"] < df.at[lastIndexTimeData_r[1], "o"]:
                    entryPrice = df.at[lastIndexTimeData[1], "c"]
                    stockAlgoLogic.entryOrder(entryPrice, stockName, 100000//entryPrice, "SELL")

            # lastIndexTimeData = timeData
            stockAlgoLogic.pnlCalculator()

        if not stockAlgoLogic.openPnl.empty:
            for index, row in stockAlgoLogic.openPnl.iterrows():
                exitType = "Time Up"
                stockAlgoLogic.exitOrder(index, exitType, (df.at[lastIndexTimeData, "c"]))
        stockAlgoLogic.pnlCalculator()


if __name__ == "__main__":
    startNow = datetime.now()

    devName = "NA"
    strategyName = "spotFutureBuyOnly_40"
    version = "v1"

    startDate = datetime(2025, 1, 1, 9, 15)
    endDate = datetime(2025, 9, 30, 15, 30)

    portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/Fno_173.md", 5)
    # portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/test1.md",1)
    # portfolio = createPortfolio("/root/akashEquityBacktestAlgos/stocksList/nifty50.md",2)

    algoLogicObj = EquityFuture(devName, strategyName, version)
    fileDir, closedPnl = algoLogicObj.runBacktest(portfolio, startDate, endDate)

    dailyReport = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endNow = datetime.now()
    print(f"Done. Ended in {endNow-startNow}")