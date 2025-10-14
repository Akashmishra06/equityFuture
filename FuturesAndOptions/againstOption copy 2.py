from backtestTools.expiry import getExpiryData, connectToMongo
from backtestTools.algoLogic import optOverNightAlgoLogic
from backtestTools.histData import getFnoBacktestData
from backtestTools.util import calculate_mtm
from datetime import datetime, time
import numpy as np
import talib as ta


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
            df_15Min = getFnoBacktestData(indexSym, startEpoch, endEpoch, "15Min",conn=conn)
        except Exception as e:
            self.strategyLogger.info(f"Data not found for {baseSym} in range {startDate} to {endDate}")
            raise Exception(e)
        df.dropna(inplace=True)
        df_15Min.dropna(inplace=True)

        df_15Min['rsi'] = ta.RSI(df_15Min['c'], timeperiod=7)
        df_15Min['callEntryTypeOne'] = np.where((df_15Min['rsi'] < 30) & (df_15Min['rsi'] < df_15Min['rsi'].shift(1)) & (df_15Min['o'] > df_15Min['c']), "callEntryTypeOne","")
        df_15Min['putEntryTypeOne'] = np.where((df_15Min['rsi'] > 70) & (df_15Min['rsi'] > df_15Min['rsi'].shift(1)) & (df_15Min['o'] < df_15Min['c']), "putEntryTypeOne","")

        df_15Min['putEntryTypeTwo'] = np.where((df_15Min['rsi'] > 30) & (df_15Min['rsi'].shift(1) < 30) & (df_15Min['rsi'] > df_15Min['rsi'].shift(1)) & (df_15Min['o'] < df_15Min['c']), "putEntryTypeTwo", "")
        df_15Min['callEntryTypeTwo'] = np.where((df_15Min['rsi'] < 70) & (df_15Min['rsi'].shift(1) > 70) & (df_15Min['rsi'] < df_15Min['rsi'].shift(1)) & (df_15Min['o'] > df_15Min['c']), "callEntryTypeTwo", "")

        df.to_csv(f"{self.fileDir['backtestResultsCandleData']}{indexName}_1Min.csv")
        df_15Min.to_csv(f"{self.fileDir['backtestResultsCandleData']}{indexName}_df_15Min.csv")

        lastIndexTimeData = [0, 0]
        lastdf15MinIndexTimeData = [0, 0]

        MonthlyExpiry = getExpiryData(startEpoch, baseSym)['MonthLast']
        expiryDatetime = datetime.strptime(MonthlyExpiry, "%d%b%y").replace(hour=15, minute=20)
        expiryEpoch= expiryDatetime.timestamp()
        lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

        DayFirstEntry = False

        for timeData in df.index:
            lastIndexTimeData.pop(0)
            lastIndexTimeData.append(timeData-60)
            if (timeData-900) in df_15Min.index:
                lastdf15MinIndexTimeData.pop(0)
                lastdf15MinIndexTimeData.append(timeData-900)  

            self.timeData = timeData
            self.humanTime = datetime.fromtimestamp(timeData)
            print(self.humanTime)

            if (self.humanTime.time() < time(9, 16)) | (self.humanTime.time() > time(15, 30)):
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
                MonthlyExpiry = getExpiryData(self.timeData+86400, baseSym)['MonthLast']
                expiryDatetime = datetime.strptime(MonthlyExpiry, "%d%b%y").replace(hour=15, minute=20)
                expiryEpoch= expiryDatetime.timestamp()

            if not self.openPnl.empty:
                for index, row in self.openPnl.iterrows():

                    symbol = row["Symbol"]
                    symSide = symbol[-2:]

                    if self.humanTime.time() >= time(15, 15):
                        exitType = "TimeUp"
                        self.exitOrder(index, exitType)

                    elif row["CurrentPrice"] <= row["Target"]:
                        exitType = "Target Hit"
                        self.exitOrder(index, exitType, row["CurrentPrice"])

                    elif row["CurrentPrice"] >= row["Stoploss"]:
                        exitType = "Stoploss Hit"
                        self.exitOrder(index, exitType, row["CurrentPrice"])

                    elif ((timeData-900) in df_15Min.index) and not self.openPnl.empty:

                        if symSide == "CE":

                            if (df_15Min.at[lastdf15MinIndexTimeData[1], "rsi"] > 70):
                                exitType = "callReversal-exit-CE"
                                self.exitOrder(index, exitType)

                            if (df_15Min.at[lastdf15MinIndexTimeData[1], "callEntryTypeTwo"] == "callEntryTypeTwo"):
                                exitType = "putEntryTypeTwo-exit-CE"
                                self.exitOrder(index, exitType)

                        elif symSide == "PE":

                            if (df_15Min.at[lastdf15MinIndexTimeData[1], "putEntryTypeTwo"] == "putEntryTypeTwo"):
                                exitType = "callEntryTypeTwo-exit-PE"
                                self.exitOrder(index, exitType)

                            elif (df_15Min.at[lastdf15MinIndexTimeData[1], "rsi"] < 30):
                                exitType = "putReversal-exit-PE"
                                self.exitOrder(index, exitType)

            if DayFirstEntry == True and self.humanTime.time() >= time(15, 15):
                DayFirstEntry = False

            if self.humanTime.time() < time(15, 15) and DayFirstEntry == True and ((timeData-900) in df_15Min.index) and self.openPnl.empty:

                if (df_15Min.at[lastdf15MinIndexTimeData[1], "callEntryTypeTwo"] == "callEntryTypeTwo"):

                    expiryEpoch = self.getCurrentExpiryEpoch(self.timeData, baseSym)
                    lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

                    try:
                        putSym = self.getPutSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                        data = self.fetchAndCacheFnoHistData(putSym, lastIndexTimeData[1],conn=conn)
                    except Exception as e:
                        self.strategyLogger.info(e)

                    target = 0.3 * data["c"]
                    stoploss = 1.5 * data["c"]
                    self.entryOrder(data["c"], putSym, lotSize, "SELL", {"Expiry": expiryEpoch,"Target": target,"Stoploss": stoploss,})
                    DayFirstEntry = False

                if (df_15Min.at[lastdf15MinIndexTimeData[1], "putEntryTypeTwo"] == "putEntryTypeTwo"):

                    expiryEpoch = self.getCurrentExpiryEpoch(self.timeData, baseSym)
                    lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

                    try:
                        callSym = self.getCallSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                        data = self.fetchAndCacheFnoHistData(callSym, lastIndexTimeData[1],conn=conn)
                    except Exception as e:
                        self.strategyLogger.info(e)

                    target = 0.3 * data["c"]
                    stoploss = 1.5 * data["c"]
                    self.entryOrder(data["c"], callSym, lotSize, "SELL", {"Expiry": expiryEpoch,"Target": target,"Stoploss": stoploss,})
                    DayFirstEntry = False

            if self.humanTime.time() < time(15, 15) and ((timeData-900) in df_15Min.index) and self.openPnl.empty:

                if (df_15Min.at[lastdf15MinIndexTimeData[1], "callEntryTypeOne"] == "callEntryTypeOne"):

                    expiryEpoch = self.getCurrentExpiryEpoch(self.timeData, baseSym)
                    lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

                    try:
                        putSym = self.getPutSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                        data = self.fetchAndCacheFnoHistData(putSym, lastIndexTimeData[1],conn=conn)
                    except Exception as e:
                        self.strategyLogger.info(e)

                    target = 0.3 * data["c"]
                    stoploss = 1.5 * data["c"]
                    self.entryOrder(data["c"], putSym, lotSize, "SELL", {"Expiry": expiryEpoch,"Target": target,"Stoploss": stoploss,})
                    DayFirstEntry = True

                if (df_15Min.at[lastdf15MinIndexTimeData[1], "putEntryTypeOne"] == "putEntryTypeOne"):

                    expiryEpoch = self.getCurrentExpiryEpoch(self.timeData, baseSym)
                    lotSize = int(getExpiryData(self.timeData, baseSym)["LotSize"])

                    try:
                        callSym = self.getCallSym(self.timeData, baseSym, df.at[lastIndexTimeData[1], "c"], MonthlyExpiry, 0, 100)
                        data = self.fetchAndCacheFnoHistData(callSym, lastIndexTimeData[1],conn=conn)
                    except Exception as e:
                        self.strategyLogger.info(e)

                    target = 0.3 * data["c"]
                    stoploss = 1.5 * data["c"]
                    self.entryOrder(data["c"], callSym, lotSize, "SELL", {"Expiry": expiryEpoch,"Target": target,"Stoploss": stoploss,})
                    DayFirstEntry = True

        self.pnlCalculator()
        self.combinePnlCsv()

        return self.closedPnl, self.fileDir["backtestResultsStrategyUid"]
    

if __name__ == "__main__":
    startTime = datetime.now()

    devName = "AM"
    strategyName = "FutureAndOption"
    version = "v1"

    startDate = datetime(2025, 5, 1, 9, 15)
    endDate = datetime(2025, 9, 30, 15, 30)

    algo = algoLogic(devName, strategyName, version)

    baseSym = "NIFTY"
    indexName = "NIFTY 50"

    closedPnl, fileDir = algo.run(startDate, endDate, baseSym, indexName)

    print("Calculating Daily Pnl")
    dr = calculate_mtm(closedPnl, fileDir, timeFrame="15T", mtm=True, equityMarket=True)

    endTime = datetime.now()
    print(f"Done. Ended in {endTime-startTime}")