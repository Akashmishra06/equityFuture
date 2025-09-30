from backtestTools.util import createPortfolio, calculateDailyReport, limitCapital, generateReportFile
from strategySelector.strategySelector import strategySelector
from datetime import datetime, timedelta


if __name__ == "__main__":
    startNow = datetime.now()

    devName = "NA"
    # strategyName = "DayOpenHighStrategy_v1_Buy"
    # strategyName = "DayOpenLowStrategy_v1_Buy"
    # strategyName = "DayOpenHighStrategy_v1_Sell"
    strategyName = "DayOpenLowStrategy_v1_Sell"
    version = "v1"

    startDate = datetime(2024, 1, 1, 9, 15)
    endDate = datetime(2025, 12, 31, 15, 30)

    portfolio = createPortfolio("/root/equityFuture/stocksList/Fno_173.md",1)

    algoLogicObj = strategySelector(devName, strategyName, version)
    fileDir, closedPnl = algoLogicObj.runBacktest(portfolio, startDate, endDate)
    
    endNow = datetime.now()
    print(f"Done. Ended in {endNow-startNow}")