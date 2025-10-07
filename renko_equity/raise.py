from backtestTools.histData import getFnoBacktestData, getEquityBacktestData
from backtestTools.algoLogic import optIntraDayAlgoLogic
from backtestTools.expiry import getExpiryData
from datetime import datetime, timedelta, time
from datetime import datetime, time
import indicators as indicators
import multiprocessing as mp
import pandas as pd
import numpy as np


class algoLogic(optIntraDayAlgoLogic):

    def run(self, startDate, endDate, baseSym, indexSym):

        startepoch = startDate.timestamp()
        endepoch = endDate.timestamp()

        try:
            df = getEquityBacktestData(indexSym, startepoch - (86400 * 30), endepoch, '1Min')
        except Exception as e:
            self.strategyLogger.info(f"Data not found for {baseSym} in range {startDate} to {endDate}: {e}")
            raise Exception(e)

        def getRenkoData(df, renkoSize):
            df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "datetime": "date",})
            renko = indicators.Renko(df)
            renko.brick_size = renkoSize
            renko.chart_type = indicators.Renko.PERIOD_CLOSE
            renkoData = renko.get_ohlc_data()

            renkoData = renkoData.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "date": "datetime",})
            renkoData["datetime2"] = renkoData["datetime"]
            renkoData.set_index("datetime2", inplace=True)
            renkoData = renkoData.reset_index().set_index("datetime2").sort_index()

            renkoData.index = (renkoData.index.values.astype(np.int64) // 10**9) - 19800
            renkoData.insert(loc=0, column="ti", value=renkoData.index)
            renkoSize = renkoSize
            return renkoData

        df = df[df.index >= startepoch]
        df.dropna(inplace=True)

        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{indexName}_1Min.csv")

        col = ['Target', 'Stoploss', 'Expiry']
        self.addColumnsToOpenPnlDf(col)

        current_day=None
        previous_renko = None
        current_renko=None

        putTradeCounter=0

        lastindextimeData = [0, 0]
        lastindextimeData_r=[0,0]

        for timeData in df.index:
            self.timeData = float(timeData)
            self.humanTime = datetime.fromtimestamp(timeData)
            new_day=self.humanTime.date()

            if current_day != new_day:
                current_day=new_day
                day_close=df.loc[df.index[0],'c']
                renkoSize=round(day_close * 0.01)
                self.strategyLogger.info(f"Datetime:{self.humanTime}\tRenkoSize:{renkoSize}\tDayClose:{day_close}")
                df_renko=getRenkoData(df,renkoSize)
                df_renko['signal']=np.where(df_renko['uptrend']==True,1,-1)
                df_renko.to_csv(f"{self.fileDir['backtestResultsCandleData']}{indexName}_Renko_{current_day}.csv")

            if self.humanTime.time() < time(9, 16) or self.humanTime.time() > time(15, 15):
                continue

            lastindextimeData.pop(0)
            lastindextimeData.append(timeData-60)
            colour_change_exit=True

            if lastindextimeData_r[1] in df_renko.index:
                current_renko = df_renko.at[lastindextimeData_r[1], 'signal']
            current_renko_value = current_renko.iloc[0] if isinstance(current_renko, pd.Series) else current_renko

            if lastindextimeData[1] in df.index:
                self.strategyLogger.info(f"Datetime:{self.humanTime}\tOpen:{df.at[lastindextimeData[1],'o']}\tHigh:{df.at[lastindextimeData[1],'h']}\tLow:{df.at[lastindextimeData[1],'l']}\tClose:{df.at[lastindextimeData[1],'c']}\tRenko:{current_renko}")

            if not self.openPnl.empty:
                for index, row in self.openPnl.iterrows():
                    try:
                        self.openPnl.at[index, 'CurrentPrice'] = df.at[lastindextimeData[1], "c"]
                    except Exception as e:
                        self.strategyLogger.info(e)
            self.pnlCalculator()

            if not self.openPnl.empty:

                for index, row in self.openPnl.iterrows():

                    if self.humanTime.time() >= time(15, 15):
                        exitType = "timeUp"
                        self.exitOrder(index, exitType, df.at[lastindextimeData[1], "c"])

                    elif row['PositionStatus'] == 1:
                        if df.at[lastindextimeData_r[1], "c"] < df.at[lastindextimeData_r[1], "o"]:
                            exitType = "longExit"
                            self.exitOrder(index, exitType, df.at[lastindextimeData[1], "c"])

                    elif row['PositionStatus'] == -1:
                        if df.at[lastindextimeData_r[1], "c"] > df.at[lastindextimeData_r[1], "o"]:
                            exitType = "shortExit"
                            self.exitOrder(index, exitType, df.at[lastindextimeData[1], "c"])

            if self.openPnl.empty and current_renko_value == +1 and putTradeCounter < 3:
                if df.at[lastindextimeData_r[1], "c"] > df.at[lastindextimeData_r[1], "o"]:
                    entryPrice = df.at[lastindextimeData[1], "c"]
                    self.entryOrder(entryPrice, baseSym, 100000//entryPrice, "BUY", {"lenRenko": len(df_renko)})

                elif df.at[lastindextimeData_r[1], "c"] < df.at[lastindextimeData_r[1], "o"]:
                    entryPrice = df.at[lastindextimeData[1], "c"]
                    self.entryOrder(entryPrice, baseSym, 100000//entryPrice, "SELL", {"lenRenko": len(df_renko)})
                    # print(len(df_renko))

                self.strategyLogger.info(f"Datetime:{self.humanTime}\tOpen:{df.at[lastindextimeData[1],'o']}\tHigh:{df.at[lastindextimeData[1],'h']}\tLow:{df.at[lastindextimeData[1],'l']}\tClose:{df.at[lastindextimeData[1],'c']}\t\tRenko: {current_renko_value}\tEntry:\tTradeCountPE:{putTradeCounter}\n")
            previous_renko = current_renko_value

            lastindextimeData_r.pop(0)
            lastindextimeData_r.append(timeData)

        self.pnlCalculator()
        self.combinePnlCsv()

if __name__ == "__main__":
    start = datetime.now()

    devName = "AM"
    strategyName = "Renko"
    version = "v1"

    startDate = datetime(2018, 1, 1, 9, 15)
    endDate = datetime(2025, 9, 30, 15, 30)

    algo = algoLogic(devName, strategyName, version)

    file_path = "/root/equityFuture/renko_equity/index.txt"

    with open(file_path, "r") as f:
        lines = f.read().splitlines()  # reads lines without \n

    # Assign values
    baseSym = lines[0].strip()   # first line
    indexName = lines[1].strip() # second line

    maxConcurrentProcesses = 4
    processes = []

    currentDate = startDate
    while currentDate <= endDate:
        startTime = datetime(currentDate.year, currentDate.month, currentDate.day, 9, 15, 0)
        endTime = datetime(currentDate.year, currentDate.month, currentDate.day, 15, 30, 0)

        p = mp.Process(target=algo.run, args=(startTime, endTime, baseSym, indexName))
        p.start()
        processes.append(p)

        if len(processes) >= maxConcurrentProcesses:
            for p in processes:
                p.join()
            processes = []

        currentDate += timedelta(days=1)

    end = datetime.now()
    print(f"Done. Ended in {end-start}.")

    output_file = "/root/equityFuture/renko_equity/check.txt"
    with open(output_file, "w") as f:
        f.write(f"yes")