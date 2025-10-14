import numpy as np
import talib as ta
from backtestTools.expiry import getExpiryData, connectToMongo
from datetime import datetime, time, timedelta
from backtestTools.algoLogic import optOverNightAlgoLogic
from backtestTools.util import calculate_mtm
from backtestTools.histData import getFnoBacktestData


class algoLogic(optOverNightAlgoLogic):

    def getCurrentExpiryEpoch(self, date, baseSym):
        expiryData = getExpiryData(date, baseSym)
        expiry = expiryData["MonthlyExpiry"]
        expiryDatetime = datetime.strptime(expiry, "%d%b%y")
        expiryDatetime = expiryDatetime.replace(hour=15, minute=20)
        expiryEpoch = expiryDatetime.timestamp()
        return expiryEpoch
    
    def run(self, startDate, endDate, baseSym, indexSym):
        conn = connectToMongo()

        col = ["Expiry"]
        self.addColumnsToOpenPnlDf(col)

        startEpoch = startDate.timestamp()
        endEpoch = endDate.timestamp()

        try:
            df = getFnoBacktestData(indexSym, startEpoch, endEpoch, "1Min",conn=conn)
        except Exception as e:
            self.strategyLogger.info(f"Data not found for {baseSym} in range {startDate} to {endDate}")
            raise Exception(e)
        df.dropna(inplace=True)

        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{indexName}_1Min.csv")

        lastIndexTimeData = [0, 0]

        # MonthlyExpiry = getExpiryData(startEpoch, baseSym)['MonthLast']
        MonthlyExpiry = getExpiryData(startEpoch, baseSym)['CurrentExpiry']
        expiryDatetime = datetime.strptime(MonthlyExpiry, "%d%b%y").replace(hour=15, minute=20)
        expiryEpoch= expiryDatetime.timestamp()
        lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

        Friday = False

        for timeData in df.index:
            lastIndexTimeData.pop(0)
            lastIndexTimeData.append(timeData-60)

            self.timeData = timeData
            self.humanTime = datetime.fromtimestamp(timeData)
            print(self.humanTime)

            if (self.humanTime.time() < time(9, 15)) | (self.humanTime.time() > time(15, 30)):
                continue
            if (self.humanTime.time() < time(9, 16)) | (self.humanTime.time() > time(15, 25)):
                continue

            if not self.openPnl.empty:
                for index, row in self.openPnl.iterrows():
                    try:
                        data = self.fetchAndCacheFnoHistData(row["Symbol"], lastIndexTimeData[1],conn=conn)
                        self.openPnl.at[index, "CurrentPrice"] = data["c"]
                    except Exception as e:
                        self.strategyLogger.info(e)

            if lastIndexTimeData[1] in df.index:
                self.strategyLogger.info(f"Datetime: {self.humanTime}\tClose: {df.at[lastIndexTimeData[1],'c']}")
            self.pnlCalculator()

            if self.humanTime.date() >= expiryDatetime.date():
                MonthlyExpiry = getExpiryData(self.timeData+86400, baseSym)['CurrentExpiry']
                expiryDatetime = datetime.strptime(MonthlyExpiry, "%d%b%y").replace(hour=15, minute=20)
                expiryEpoch= expiryDatetime.timestamp()
                Friday = True

            if not self.openPnl.empty:
                for index, row in self.openPnl.iterrows():

                    symbol = row["Symbol"]
                    symSide = symbol[-2:]

                    if self.humanTime.time() < time(15, 0):
                        exitType = "Dayover"
                        self.exitOrder(index, exitType)

            if Friday == True and ((timeData-60) in df.index) and self.openPnl.empty and self.humanTime.time() >= time(15, 20):

                expiryEpoch = self.getCurrentExpiryEpoch(self.timeData, baseSym)
                lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

                try:
                    callSym = self.getCallSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                    data = self.fetchAndCacheFnoHistData(callSym, lastIndexTimeData[1],conn=conn)
                    putSym = self.getPutSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                    data_put = self.fetchAndCacheFnoHistData(putSym, lastIndexTimeData[1],conn=conn)
                except Exception as e:
                    self.strategyLogger.info(e)

                self.entryOrder(data["c"], callSym, lotSize, "BUY", {"Expiry": expiryEpoch})
                self.entryOrder(data_put["c"], putSym, lotSize, "BUY", {"Expiry": expiryEpoch})
                Friday = False
                    
        self.pnlCalculator()
        self.combinePnlCsv()

        return self.closedPnl, self.fileDir["backtestResultsStrategyUid"]
    

if __name__ == "__main__":
    startTime = datetime.now()

    devName = "AM"
    strategyName = "FridayOptionBuyOvernight"
    version = "v1"

    startDate = datetime(2020, 1, 1, 9, 15)
    endDate = datetime(2025, 10, 10, 15, 30)

    algo = algoLogic(devName, strategyName, version)

    baseSym = "NIFTY"
    indexName = "NIFTY 50"

    closedPnl, fileDir = algo.run(startDate, endDate, baseSym, indexName)

    print("Calculating Daily Pnl")
    dr = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endTime = datetime.now()
    print(f"Done. Ended in {endTime-startTime}")