from strategies.DayOpenHighStrategy_v1_Buy import DayOpenHighStrategy_v1_Buy
from strategies.DayOpenLowStrategy_v1_Buy import DayOpenLowStrategy_v1_Buy
from strategies.DayOpenHighStrategy_v1_Sell import DayOpenHighStrategy_v1_Sell
from strategies.DayOpenLowStrategy_v1_Sell import DayOpenLowStrategy_v1_Sell


def strategySelector(devName, strategyName, version):


    if strategyName == "DayOpenHighStrategy_v1_Sell":

        return DayOpenHighStrategy_v1_Sell(devName, strategyName, version)
    
    if strategyName == "DayOpenLowStrategy_v1_Sell":

        return DayOpenLowStrategy_v1_Sell(devName, strategyName, version)
    
    if strategyName == "DayOpenLowStrategy_v1_Buy":

        return DayOpenLowStrategy_v1_Buy(devName, strategyName, version)
    
    if strategyName == "DayOpenHighStrategy_v1_Buy":

        return DayOpenHighStrategy_v1_Buy(devName, strategyName, version)

    else:

        raise Exception("Strategy Name Mismatch")