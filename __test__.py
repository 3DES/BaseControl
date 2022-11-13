import GridLoad.EasyMeter
from datetime import datetime


def ASSERT(trueValue : bool = False):
    if not trueValue:
        raise Exception("assertion failed")


def baseTests():
    from Base.Base import Base
    from Base.Supporter import Supporter

    myBase = Base("myByse", {})

    while True:
        myBase = Base("XX", {})
        if myBase.timer("T1", timeout = 5, firstTimeTrue = True):
            if not hasattr(myBase, "msgCtr1"):
                myBase.msgCtr1 = 0
            myBase.msgCtr1 += 1
            print(f"TIMING EVENT T1: {myBase.msgCtr1} {Supporter.getTimeStamp()}")


class EasyMeterTest(GridLoad.EasyMeter.EasyMeter):
    def __init__(self):
        # preparations and constructor test
        def dummy(*params):
            pass
        from Base.ThreadObject import ThreadObject
        self.name = "EasyMeterTest"
        self.configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
            "gridLossThreshold" : 60,
            "messageInterval"   : 60,
        }
        ThreadObject.__init__ = dummy
        super().__init__(self, "myEasyMeter", {})
        
        # test prepareNewEasyMeterMessage()
        self.energyValues[self.ENERGY_VALUE_NAMES["backedupEnergyLevel"]] = 0
        self.energyValues[self.ENERGY_VALUE_NAMES["currentEnergyLevel"]] = 0
        self.energyValues[self.ENERGY_VALUE_NAMES["lastSentEnergyValue"]] = 0
        self.gridLossDetected = False
        self.lastEasyMeterMessageTime = 0

        self.prepareNewEasyMeterMessage()

        ASSERT(self.energyData["previousPower"]     == 0) 
        ASSERT(self.energyData["previousReduction"] == 0) 
        ASSERT(self.energyData["previousTimestamp"] == 0) 
        ASSERT(self.energyData["allowedPower"]      == 0) 
        ASSERT(self.energyData["allowedReduction"]  == 0) 
        ASSERT(self.energyData["allowedTimestamp"]  != 0) 
        ASSERT(self.energyData["updatePowerValue"]  == True)
        ASSERT(self.gridLossDetected                == False) 
        ASSERT(self.lastEasyMeterMessageTime        != 0)


'''
Test main function
'''
if __name__ == '__main__':
    #baseTests()
    EasyMeterTest()

