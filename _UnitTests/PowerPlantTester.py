from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
import time


class PowerPlantTester(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)


    def fakeSchitWetterHeute(self):
        data = {"lastrequest": 13, "Tag_0": {"Sonnenstunden": 0, "Datum": "04.12."}, "Tag_1": {"Sonnenstunden": 15, "Datum": "05.12."}, "Tag_2": {"Sonnenstunden": 0, "Datum": "06.12."}, "Tag_3": {"Sonnenstunden": 1, "Datum": "07.12."}} 
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic("Wetter")), data, globalPublish = False, enableEcho = False)

    def fakeSchitWetterMorgen(self):
        data = {"lastrequest": 13, "Tag_0": {"Sonnenstunden": 15, "Datum": "04.12."}, "Tag_1": {"Sonnenstunden": 0, "Datum": "05.12."}, "Tag_2": {"Sonnenstunden": 0, "Datum": "06.12."}, "Tag_3": {"Sonnenstunden": 1, "Datum": "07.12."}} 
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic("Wetter")), data, globalPublish = False, enableEcho = False)

    def fakeSchitWetterHeuteUndMorgen(self):
        data = {"lastrequest": 13, "Tag_0": {"Sonnenstunden": 0, "Datum": "04.12."}, "Tag_1": {"Sonnenstunden": 0, "Datum": "05.12."}, "Tag_2": {"Sonnenstunden": 0, "Datum": "06.12."}, "Tag_3": {"Sonnenstunden": 1, "Datum": "07.12."}} 
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic("Wetter")), data, globalPublish = False, enableEcho = False)

    def fakeGutesWetter(self):
        data = {"lastrequest": 13, "Tag_0": {"Sonnenstunden": 15, "Datum": "04.12."}, "Tag_1": {"Sonnenstunden": 15, "Datum": "05.12."}, "Tag_2": {"Sonnenstunden": 0, "Datum": "06.12."}, "Tag_3": {"Sonnenstunden": 1, "Datum": "07.12."}} 
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic("Wetter")), data, globalPublish = False, enableEcho = False)


    def fakeInverterAkkumode(self):
        data = {"Netzspannung": 231, "AcOutSpannung": 231.6, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "B", "DailyProduction": 0.0, "CompleteProduction": 0, "DailyCharge": 0.0, "DailyDischarge": 0.0, "BattCapacity": 30, "DeviceStatus2": "000", "BattSpannung": 49.7}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["inverterName"])), data, globalPublish = False, enableEcho = False)

    def fakeInverterNetzmode(self):
        data = {"Netzspannung": 231, "AcOutSpannung": 0, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "L", "DailyProduction": 0.0, "CompleteProduction": 0, "DailyCharge": 0.0, "DailyDischarge": 0.0, "BattCapacity": 30, "DeviceStatus2": "000", "BattSpannung": 49.7}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["inverterName"])), data, globalPublish = False, enableEcho = False)


    def fakeBMSUnterSpannung(self):
        data = {"Vmin": 0.0, "Vmax": 3.0, "Ladephase": "none", "toggleIfMsgSeen": False, "BmsEntladeFreigabe": False}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["bmsName"])), data, globalPublish = False, enableEcho = False)

    def fakeBMSNormalBetrieb(self):
        data = {"Vmin": 0.0, "Vmax": 3.0, "Ladephase": "none", "toggleIfMsgSeen": False, "BmsEntladeFreigabe": True}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["bmsName"])), data, globalPublish = False, enableEcho = False)

    def initPowerplant(self):
        data = {
            "WrNetzladen"                        : False,
            "Akkuschutz"                         : False,
            "RussiaMode"                         : False,
            "Error"                              : False,
            "PowerSaveMode"                      : False,
            "WrMode"                             : "Akku",
            "AutoMode"                           : True,
            "schaltschwelleAkku"                 : 20.0,
            "schaltschwelleNetz"                 : 10.0,
            "schaltschwelleAkkuTollesWetter"     : 20.0,
            "schaltschwelleAkkuRussia"           : 100.0,
            "schaltschwelleNetzRussia"           : 80.0,
            "schaltschwelleAkkuSchlechtesWetter" : 45.0,
            "schaltschwelleNetzSchlechtesWetter" : 30.0,
            "schaltschwelleNetzLadenAus"         : 12.0,
            "schaltschwelleNetzLadenEin"         : 6.0,
            "MinSoc"                             : 10.0,
            "SchaltschwelleAkkuTollesWetter"     : 20.0,
            "AkkuschutzAbschalten"               : 60.0,
            "verbrauchNachtAkku"                 : 25.0,
            "verbrauchNachtNetz"                 : 3.0,
            "wetterSchaltschwelleNetz"           : 6
        }
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["powerPlantName"])), data, globalPublish = True, enableEcho = False)

    def setAkkuSoc(self, prozent):
        data = { "Ah":-1, "Current":0, "Prozent": prozent}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["socMonitorName"])), data, globalPublish = False, enableEcho = False)

    def testBoolAndLog(self, value, name):
        if value:
            self.logger.info(self, f"Passed! {name}")
            Supporter.debugPrint(f"Passed! {name}", color = "GREEN")
        else:
            self.logger.error(self, f"Error! {name}")
            Supporter.debugPrint(f"Error! {name}", color = "RED")

    def assertBoolFromProwerPlant(self, key, value, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]][key] == value, name)

    def assertAkkuBerieb(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["WrMode"] == "Akku", name)

    def assertNetzBerieb(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["WrMode"] == "Netz", name)

    def assertNetzLaden(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["WrNetzladen"], name)

    def assertNetzLadenAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powerPlantName"]]["WrNetzladen"], name)

    def assertAkkuschhutz(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["Akkuschutz"], name)

    def assertAkkusschutzAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powerPlantName"]]["Akkuschutz"], name)

    def assertError(self, checkMsg = True, name=""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["Error"], name)

    def assertErrorAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powerPlantName"]]["Error"], name)

    def assertAutoMode(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powerPlantName"]]["AutoMode"], name)

    def assertManualMode(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powerPlantName"]]["AutoMode"], name)

    def getPowerPlantValue(self, name):
        if type(self.localDeviceData[self.configuration["powerPlantName"]][name]) == float:
            return int(self.localDeviceData[self.configuration["powerPlantName"]][name])
        else:
            return self.localDeviceData[self.configuration["powerPlantName"]][name]

    def setPowerPlantBoolValueAndAssert(self, key, value, name=""):
        if not type(value) == bool:
            raise Exception("Wrong data type")
        self.mqttPublish(self.createInTopic(ThreadObject.createProjectTopic(self.configuration["powerPlantName"])), {key:value}, globalPublish = False, enableEcho = False)
        self.assertBoolFromProwerPlant(key, value, True, name)

    def cycleSocAndAssert(self, start, end, assertFunktion):
        if end>start:
            iterateList = list(range(start, end+1))
        else:
            iterateList = list(range(start, end-1, -1))

        for soc in iterateList:
            self.setAkkuSoc(soc)
            self.wartenUndMsgTest(waitTime = 0.2, minMsg = 0, maxMsg = 0)
            assertFunktion(False, str(soc))

    def myDateTime(self):
        pass

    def handleMessage(self, message):
        """
        sort the incoming msg to the localDeviceData variable
        handle expectedDevicesPresent variable
        set setable values wich are received global
        """

        # check if a expected device sent a msg and store it
        for key in self.deviceList:
            if key in message["topic"]:
                if not key in self.localDeviceData:
                    self.localDeviceData[key] = {} 
                self.localDeviceData[key].update(message["content"])

    def wartenUndMsgTest(self, waitTime = 6, minMsg = 1, maxMsg = 2):
        # We loop x seconds, take and count the msg, test the msg counter on min and max
        msgCounter = 0
        while not self.timer(name = "timeoutMsg", timeout = waitTime):
            time.sleep(0.1) # be nice to other threads
            while not self.mqttRxQueue.empty():
                newMqttMessageDict = self.readMqttQueue(error = False)
                self.handleMessage(newMqttMessageDict)
                msgCounter += 1
        self.timer(name = "timeoutMsg", remove = True)
        if not (minMsg <= msgCounter <= maxMsg):
            self.logger.error(self, f"Wrong count of msg: {msgCounter}")


# Test Funktion Helpers
    def initAkkumodeAndAssert(self):
        self.TestName = "Init Akkumode and assert"
        self.printTestBeginnAndIncrTestNumber()
        self.initPowerplant()
        self.fakeBMSNormalBetrieb()
        self.fakeInverterAkkumode()
        self.fakeGutesWetter()
        self.setAkkuSoc(50)
        self.assertAkkusschutzAus(checkMsg=True)
        self.assertAutoMode(checkMsg=False)
        self.assertNetzLadenAus(checkMsg=False)
        self.assertAkkuBerieb(checkMsg=False, name=self.getTestResultMsg())


    def cycleAndCheckSwitchValue(self, name, assertFuntionBevoreChange, assertFuntionAfterChange, startKeyname, endKeyname, offsetStartVal = False):
        self.TestName = name
        self.printTestBeginnAndIncrTestNumber()
        if type(startKeyname) == str:
            startValue = self.getPowerPlantValue(startKeyname)
        else:
            startValue = startKeyname
        if type(endKeyname) == str:
            endValue = self.getPowerPlantValue(endKeyname)
        else:
            endValue = endKeyname
        startOffset = 0
        if startValue<endValue:
            endOffset = -1
            if offsetStartVal:
                startOffset = 1
        else:
            endOffset = 1
            if offsetStartVal:
                startOffset = -1
        self.cycleSocAndAssert(startValue+startOffset, endValue+endOffset, assertFuntionBevoreChange)
        self.logger.info(self, f"Set to endValue: {endValue}")
        self.setAkkuSoc(endValue)
        assertFuntionAfterChange(checkMsg=True, name=self.getTestResultMsg())

    def printTestBeginnAndIncrTestNumber(self):
        self.TestNumber += 1
        self.logger.info(self, f"__________________Test {self.TestNumber} --{self.TestName}-- beginnt__________________")

    def getTestResultMsg(self):
        return f"************** Test {self.TestNumber} --{self.TestName}-- beendet **************"

    def setToMinSocAssertNetzBetrieb(self):
        self.TestName = "Netzbetrieb nach unterschreiten von minsoc"
        self.printTestBeginnAndIncrTestNumber()
        self.setAkkuSoc(self.getPowerPlantValue("MinSoc"))
        self.assertAkkusschutzAus(checkMsg=True)
        self.assertAutoMode(checkMsg=False)
        self.assertNetzLadenAus(checkMsg=False)
        self.assertNetzBerieb(checkMsg=False, name=self.getTestResultMsg())


    def threadInitMethod(self):
        self.deviceList = []
        self.deviceList.append(self.configuration["powerPlantName"])
        self.deviceList.append(self.configuration["inverterName"])
        # @todo UsbRelaisName
        self.localDeviceData = {}
        self.tagsIncluded(["bmsName", "socMonitorName", "inverterName", "powerPlantName"])
        self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(self.configuration["powerPlantName"])), globalSubscription = True)
        self.mqttSubscribeTopic(self.createInTopicFilter(self.createProjectTopic(self.configuration["inverterName"])), globalSubscription = False)
        self.TestNumber = 0
        self.TestName = ""

#        ThreadObject.PowerPlant.datetime.datetime.now = self.myDateTime

    def threadMethod(self):
        time.sleep(1) # short delay because of subscribe of powerplant maybe is not finished
        self.initAkkumodeAndAssert()

        self.cycleAndCheckSwitchValue("teste auf Netz wenn MinSoc unterschritten wird",self.assertAkkuBerieb, self.assertNetzBerieb, "schaltschwelleAkku", "MinSoc")
        # jetzt sind wir im Netzbetrieb nach erreichen des MinSoc

        # Wir pruefen jetzt die umschaltung auf Akku
        self.cycleAndCheckSwitchValue("Akkubetrieb nach MinSoc",self.assertNetzBerieb, self.assertAkkuBerieb, "MinSoc", "schaltschwelleAkkuTollesWetter")



        # Wir unterschreiten minSoc und lösen eine Unterspannungs erkennung vom BMS aus
        self.setToMinSocAssertNetzBetrieb()
        self.fakeBMSUnterSpannung()
        self.assertNetzLaden(True, "Netzladen nach Unterspannung ein")

        # Wir pruefen jetzt ob NetzLaden an bleibt weil Unterspannungserkennung noch anliegt
        # Fehler: Wrong count of msg: 0 ist normal
        self.cycleSocAndAssert(self.getPowerPlantValue("MinSoc"), self.getPowerPlantValue("schaltschwelleNetzLadenAus"), self.assertNetzLaden)
        self.fakeBMSNormalBetrieb()




        # Wir pruefen jetzt das Umschalten auf Akku im Normalbetrieb
        self.setAkkuSoc(10)
        self.fakeBMSUnterSpannung()
        self.assertNetzLaden(False, "Netzladen nach Unterspannung ein")
        self.fakeBMSNormalBetrieb()
        self.cycleAndCheckSwitchValue("Netzladen aus ab Schwelle bei Normalbetrieb",self.assertNetzLaden, self.assertNetzLadenAus, "MinSoc", "schaltschwelleNetzLadenAus")
        # teste erneutes einschalten des Ladens
        self.cycleAndCheckSwitchValue("Erneutes einschalten Netzladen",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzLadenAus", "schaltschwelleNetzLadenEin")
        # teste auf Netzladen aus
        self.cycleAndCheckSwitchValue("Netzladen aus ab Schwelle bei Normalbetrieb",self.assertNetzLaden, self.assertNetzLadenAus, "schaltschwelleNetzLadenEin", "schaltschwelleNetzLadenAus")





        # Wir pruefen jetzt die Russia Mode (USV Mode)
        self.assertNetzLadenAus(checkMsg=False, name="Pruefe Startsbedingung USV Mode Test")
        self.assertErrorAus(checkMsg=False)
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleAkku"))
        self.assertAkkuBerieb(checkMsg=True, name="Akkubetrieb nach setzen von Soc auf schaltschwelleAkku")
        self.setPowerPlantBoolValueAndAssert("RussiaMode", True)
        self.assertNetzBerieb(checkMsg=False, name="Test NetzLaden nach einschalten von Russia Mode und geringen Soc")
        self.assertNetzLaden(checkMsg=False)

        # teste auf Netzladen aus wenn schaltschwelle Netz im Russia Mode erreicht ist
        self.cycleAndCheckSwitchValue("Netzladen aus bei USV Mode",self.assertNetzLaden, self.assertNetzLadenAus, "schaltschwelleAkkuTollesWetter", "schaltschwelleNetzRussia")

        # teste auf Netzladen ein wenn schaltschwelle Netz - verbrauchNachtNetz erreicht ist
        self.cycleAndCheckSwitchValue("Netzladen ein bei USV Mode",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzRussia", self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"))

        self.cycleAndCheckSwitchValue("Netzladen aus bei USV Mode",self.assertNetzLaden, self.assertNetzLadenAus, self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"), "schaltschwelleNetzRussia",)

        # teste auf Akkubetrieb im Russia Mode
        self.cycleAndCheckSwitchValue("Akkubetieb bei USV Mode",self.assertNetzBerieb, self.assertAkkuBerieb, "schaltschwelleNetzRussia", "schaltschwelleAkkuRussia")

        # teste auf Netzbetrieb im Russia Mode
        self.cycleAndCheckSwitchValue("Netzbetrieb bei USV Mode",self.assertAkkuBerieb, self.assertNetzBerieb, "schaltschwelleAkkuRussia", "schaltschwelleNetzRussia")

        # teste auf Netzladen ein wenn schaltschwelle Netz - verbrauchNachtNetz erreicht ist
        self.cycleAndCheckSwitchValue("Netzladen ein bei USV Mode",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzRussia", self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"))
        self.setPowerPlantBoolValueAndAssert("RussiaMode", False)
        self.assertNetzLadenAus(checkMsg=False, name="Netzladen aus nach schalten auf Autobetrieb")
        self.assertAkkuBerieb(checkMsg=False, name="Akkubetrieb nach schalten auf Autobetrieb")





        # teste das Verhalten wenn eine Unterspannung auftritt und der SOC größer als NetzLaden aus ist
        self.TestName = "Unterspannung zu hoher SOC. SOC unplausibel Test"
        self.printTestBeginnAndIncrTestNumber()
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleNetzLadenAus") + 1)
        self.assertNetzLadenAus(checkMsg=False, name="Pruefe Startsbedingung Unterspannung SOC unplausibel Test")
        self.assertAkkuBerieb(checkMsg=False)
        self.assertErrorAus(checkMsg=False)
        self.fakeBMSUnterSpannung()
        self.assertNetzBerieb(checkMsg=True, name="Netzbetrieb nach Unterspannung")
        self.fakeBMSNormalBetrieb()
        self.assertNetzLaden(checkMsg=False)
        self.assertErrorAus(checkMsg=False)
        self.assertAkkuschhutz(checkMsg=False)

        # teste auf Umschaltung auf Akku wenn SOC > schaltschwelleAkkuSchlechtesWetter
        self.cycleAndCheckSwitchValue("Netzladen ein bis schaltschwelleAkkuSchlechtesWetter erreicht ist",self.assertNetzLaden, self.assertAkkuBerieb, "schaltschwelleNetzLadenAus", "schaltschwelleAkkuSchlechtesWetter")
        self.assertNetzLadenAus(checkMsg=False)

        # PowerPlant wieder in den Akkubetrieb setzen
        self.setPowerPlantBoolValueAndAssert("Akkuschutz", False)

        self.TestName = "Unterspannung zu hoher SOC. SOC Fehler Test"
        self.printTestBeginnAndIncrTestNumber()
        # teste das Verhalten wenn eine Unterspannung auftritt und der SOC größer als schaltschwelleAkkuTollesWetter aus ist
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleAkkuTollesWetter") + 1)
        self.assertNetzLadenAus(checkMsg=False, name="Pruefe Startsbedingung Unterspannung SOC Fehler Test")
        self.assertAkkuBerieb(checkMsg=False)
        self.assertErrorAus(checkMsg=False)
        self.fakeBMSUnterSpannung()
        self.assertNetzBerieb(checkMsg=True, name="Netzbetrieb nach Unterspannung")
        self.fakeBMSNormalBetrieb()
        self.assertNetzLaden(checkMsg=False)
        self.assertError(checkMsg=False)

        # teste dass der powerplant im Fehlerfall nicht mehr regelt
        self.TestName = "Netzladen ein, egal welcher Akkustand"
        self.printTestBeginnAndIncrTestNumber()
        self.cycleSocAndAssert(1, 101, self.assertNetzLaden)




        self.localDeviceData
        self.logger.info(self, "Test abgeschlossen")
        raise Exception("Test abgeschlossen") 


    def threadBreak(self):
        pass