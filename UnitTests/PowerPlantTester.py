import json
from Base.ThreadObject import ThreadObject
import datetime


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
        data = {"WrNetzladen": False, "Akkuschutz": False, "RussiaMode": False, "Error": False, "PowerSaveMode": False, "WrMode": "Akku", "AutoMode": True, "schaltschwelleAkku": 20.0, "schaltschwelleNetz": 10.0, "schaltschwelleAkkuTollesWetter": 20.0, "schaltschwelleAkkuRussia": 100.0, "schaltschwelleNetzRussia": 80.0, "schaltschwelleAkkuSchlechtesWetter": 45.0, "schaltschwelleNetzSchlechtesWetter": 30.0, "schaltschwelleNetzLadenaus": 12.0, "schaltschwelleNetzLadenein": 6.0, "MinSoc": 10.0, "SchaltschwelleAkkuTollesWetter": 20.0, "AkkuschutzAbschalten": 60.0, "verbrauchNachtAkku": 25.0, "verbrauchNachtNetz": 3.0, "wetterSchaltschwelleNetz": 6}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["powePlantName"])), data, globalPublish = True, enableEcho = False)

    def setAkkuSoc(self, prozent):
        data = { "Ah":-1, "Current":0, "Prozent": prozent}
        self.mqttPublish(self.createOutTopic(ThreadObject.createProjectTopic(self.configuration["socMonitorName"])), data, globalPublish = False, enableEcho = False)

    def testBoolAndLog(self, value, name):
        if value:
            self.logger.info(self, f"Passed! {name}")
        else:
            self.logger.error(self, f"Error! {name}")

    def assertBoolFromProwerPlant(self, key, value, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]][key] == value, name)

    def assertAkkuBerieb(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["WrMode"] == "Akku", name)

    def assertNetzBerieb(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["WrMode"] == "Netz", name)

    def assertNetzLaden(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["WrNetzladen"], name)

    def assertNetzLadenAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powePlantName"]]["WrNetzladen"], name)

    def assertAkkuschhutz(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["Akkuschutz"], name)

    def assertAkkusschutzAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powePlantName"]]["Akkuschutz"], name)

    def assertError(self, checkMsg = True, name=""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["Error"], name)

    def assertErrorAus(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powePlantName"]]["Error"], name)

    def assertAutoMode(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(self.localDeviceData[self.configuration["powePlantName"]]["AutoMode"], name)

    def assertManualMode(self, checkMsg = True, name = ""):
        if checkMsg:
            self.wartenUndMsgTest()
        self.testBoolAndLog(not self.localDeviceData[self.configuration["powePlantName"]]["AutoMode"], name)

    def getPowerPlantValue(self, name):
        if type(self.localDeviceData[self.configuration["powePlantName"]][name]) == float:
            return int(self.localDeviceData[self.configuration["powePlantName"]][name])
        else:
            return self.localDeviceData[self.configuration["powePlantName"]][name]

    def setPowerPlantBoolValueAndAssert(self, key, value, name=""):
        if not type(value) == bool:
            raise Exception("Wrong value type")
        self.mqttPublish(self.createInTopic(ThreadObject.createProjectTopic(self.configuration["powePlantName"])), {key:value}, globalPublish = False, enableEcho = False)
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

        # check if a expected device sended a msg and store it
        for key in self.deviceList:
            if key in message["topic"]:
                self.localDeviceData[key] = message["content"]

    def wartenUndMsgTest(self, waitTime = 3, minMsg = 1, maxMsg = 2):
        # We loop x seconds, take and count the msg, test the msg counter on min and max
        msgCounter = 0
        while not self.timer(name = "timeoutMsg", timeout = waitTime):
            while not self.mqttRxQueue.empty():
                newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
                self.logger.info(self, "received message :" + str(newMqttMessageDict["content"]))
                try:
                    newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
                except:
                    pass
                self.handleMessage(newMqttMessageDict)
                msgCounter += 1
        self.timer(name = "timeoutMsg", remove = True)
        if not (minMsg <= msgCounter <= maxMsg):
            self.logger.error(self, f"Wrong count of msg: {msgCounter}")


# Test Funktion Helpers
    def initAkkumodeAndAssert(self, testNr):
        self.logger.info(self, f"Test {testNr} beginn")
        self.initPowerplant()
        self.fakeBMSNormalBetrieb()
        self.fakeInverterAkkumode()
        self.fakeGutesWetter()
        self.setAkkuSoc(50)
        self.assertAkkusschutzAus(checkMsg=True)
        self.assertAutoMode(checkMsg=False)
        self.assertNetzLadenAus(checkMsg=False)
        self.assertAkkuBerieb(checkMsg=False, name=f"Test {testNr} Akkubetrieb nach Start")

    def cycle100ToNearlyMinSocAssertAkkuBetrieb(self, testNr):
        self.logger.info(self, f"Test {testNr} beginn")
        self.cycleSocAndAssert(100, self.getPowerPlantValue("MinSoc")+1, self.assertAkkuBerieb)
        self.assertAkkuBerieb(checkMsg=False, name=f"Test {testNr} Akkubetrieb nach Zyklus")


    def cycleAndCheckSwitchValue(self, testNr, name, assertFuntionBevoreChange, assertFuntionAfterChange, startKeyname, endKeyname, offsetStartVal = False):
        if type(startKeyname) == str:
            startValue = self.getPowerPlantValue(startKeyname)
        else:
            startValue = startKeyname
        if type(endKeyname) == str:
            endValue = self.getPowerPlantValue(endKeyname)
        else:
            endValue = endKeyname
        self.logger.info(self, f"Test {testNr} beginn, {name}")
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
        assertFuntionAfterChange(checkMsg=True, name=f"Test {testNr} {name}")

    def printTestBeginnAndIncrTestNumber(self, name=""):
        self.testNumber =+1
        self.logger.info(self, f"Test {self.testNumber} {name} beginnt")


    def setToMinSocAssertNetzBetrieb(self, testNr):
        self.logger.info(self, f"Test {testNr} beginn")
        self.setAkkuSoc(self.getPowerPlantValue("MinSoc"))
        self.assertAkkusschutzAus(checkMsg=True)
        self.assertAutoMode(checkMsg=False)
        self.assertNetzLadenAus(checkMsg=False)
        self.assertNetzBerieb(checkMsg=False, name=f"Test {testNr} Netzbetrieb nach unterschreiten von minsoc")


    def threadInitMethod(self):
        self.deviceList = []
        self.deviceList.append(self.configuration["powePlantName"])
        self.deviceList.append(self.configuration["inverterName"])
        # @todo UsbRelaisName
        self.localDeviceData = {}
        self.tagsIncluded(["bmsName", "socMonitorName", "inverterName", "powePlantName"])
        self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(self.configuration["powePlantName"])), globalSubscription = True)
        self.mqttSubscribeTopic(self.createInTopicFilter(self.createProjectTopic(self.configuration["inverterName"])), globalSubscription = False)
        self.testNumber = 0

#        ThreadObject.PowerPlant.datetime.datetime.now = self.myDateTime

    def threadMethod(self):

        self.initAkkumodeAndAssert(1)

        self.cycleAndCheckSwitchValue(2, "teste auf Netz wenn MinSoc unterschritten wird",self.assertAkkuBerieb, self.assertNetzBerieb, "schaltschwelleAkku", "MinSoc")
        # jetzt sind wir im Netzbetrieb nach erreichen des MinSoc

        # Wir pruefen jetzt die umschaltung auf Akku
        self.cycleAndCheckSwitchValue(4, "Akkubetrieb nach MinSoc",self.assertNetzBerieb, self.assertAkkuBerieb, "MinSoc", "schaltschwelleAkkuTollesWetter")



        # Wir unterschreiten minSoc und lösen eine Unterspannungs erkennung vom BMS aus
        self.setToMinSocAssertNetzBetrieb(5)
        self.fakeBMSUnterSpannung()
        self.assertNetzLaden(True, "Netzladen nach Unterspannung ein")

        # Wir pruefen jetzt ob NetzLaden an bleibt weil Unterspannungserkennung noch anliegt
        # Fehler: Wrong count of msg: 0 ist normal
        self.cycleSocAndAssert(self.getPowerPlantValue("MinSoc"), self.getPowerPlantValue("schaltschwelleNetzLadenaus"), self.assertNetzLaden)
        self.fakeBMSNormalBetrieb()




        # Wir pruefen jetzt das Umschalten auf Akku im Normalbetrieb
        self.setAkkuSoc(10)
        self.fakeBMSUnterSpannung()
        self.assertNetzLaden(False, "Netzladen nach Unterspannung ein")
        self.fakeBMSNormalBetrieb()
        self.cycleAndCheckSwitchValue(7, "Netzladen aus ab Schwelle bei Normalbetrieb",self.assertNetzLaden, self.assertNetzLadenAus, "MinSoc", "schaltschwelleNetzLadenaus")
        # teste erneutes einschalten des Ladens
        self.cycleAndCheckSwitchValue(8, "Erneutes einschalten Netzladen",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzLadenaus", "schaltschwelleNetzLadenein")
        # teste auf Netzladen aus
        self.cycleAndCheckSwitchValue(9, "Netzladen aus ab Schwelle bei Normalbetrieb",self.assertNetzLaden, self.assertNetzLadenAus, "schaltschwelleNetzLadenein", "schaltschwelleNetzLadenaus")





        # Wir pruefen jetzt die Russia Mode (USV Mode)
        self.assertNetzLadenAus(checkMsg=False, name="Pruefe Startsbedingung USV Mode Test")
        self.assertErrorAus(checkMsg=False)
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleAkku"))
        self.assertAkkuBerieb(checkMsg=True, name="Akkubetrieb nach setzen von Soc auf schaltschwelleAkku")
        self.setPowerPlantBoolValueAndAssert("RussiaMode", True)
        self.assertNetzBerieb(checkMsg=False, name="Test NetzLaden nach einschalten von Russia Mode und geringen Soc")
        self.assertNetzLaden(checkMsg=False)

        # teste auf Netzladen aus wenn schaltschwelle Netz im Russia Mode erreicht ist
        self.cycleAndCheckSwitchValue(10, "Netzladen aus bei USV Mode",self.assertNetzLaden, self.assertNetzLadenAus, "schaltschwelleAkkuTollesWetter", "schaltschwelleNetzRussia")

        # teste auf Netzladen ein wenn schaltschwelle Netz - verbrauchNachtNetz erreicht ist
        self.cycleAndCheckSwitchValue(11, "Netzladen ein bei USV Mode",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzRussia", self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"))

        self.cycleAndCheckSwitchValue(12, "Netzladen aus bei USV Mode",self.assertNetzLaden, self.assertNetzLadenAus, self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"), "schaltschwelleNetzRussia",)

        # teste auf Akkubetrieb im Russia Mode
        self.cycleAndCheckSwitchValue(13, "Akkubetieb bei USV Mode",self.assertNetzBerieb, self.assertAkkuBerieb, "schaltschwelleNetzRussia", "schaltschwelleAkkuRussia")

        # teste auf Netzbetrieb im Russia Mode
        self.cycleAndCheckSwitchValue(14, "Netzbetrieb bei USV Mode",self.assertAkkuBerieb, self.assertNetzBerieb, "schaltschwelleAkkuRussia", "schaltschwelleNetzRussia")

        # teste auf Netzladen ein wenn schaltschwelle Netz - verbrauchNachtNetz erreicht ist
        self.cycleAndCheckSwitchValue(15, "Netzladen ein bei USV Mode",self.assertNetzLadenAus, self.assertNetzLaden, "schaltschwelleNetzRussia", self.getPowerPlantValue("schaltschwelleNetzRussia") - self.getPowerPlantValue("verbrauchNachtNetz"))
        self.setPowerPlantBoolValueAndAssert("RussiaMode", False)
        self.assertNetzLadenAus(checkMsg=False, name="Netzladen aus nach schalten auf Autobetrieb")
        self.assertAkkuBerieb(checkMsg=False, name="Akkubetrieb nach schalten auf Autobetrieb")




        # teste das Verhalten wenn einen Unterspannung auftritt und der SOC größer als NetzLaden aus ist
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleNetzLadenaus") + 1)
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
        self.cycleAndCheckSwitchValue(16, "Netzladen ein bis schaltschwelleAkkuSchlechtesWetter erreicht ist",self.assertNetzLaden, self.assertAkkuBerieb, "schaltschwelleNetzLadenaus", "schaltschwelleAkkuSchlechtesWetter")
        self.assertNetzLadenAus(checkMsg=False)

        # PowerPlant wieder in den Akkubetrieb setzen
        self.setPowerPlantBoolValueAndAssert("Akkuschutz", False)

        # teste das Verhalten wenn einen Unterspannung auftritt und der SOC größer als schaltschwelleAkkuTollesWetter aus ist
        self.setAkkuSoc(self.getPowerPlantValue("schaltschwelleAkkuTollesWetter") + 1)
        self.assertNetzLadenAus(checkMsg=False, name="Pruefe Startsbedingung Unterspannung SOC Fehler Test")
        self.assertAkkuBerieb(checkMsg=False)
        self.assertErrorAus(checkMsg=False)
        self.fakeBMSUnterSpannung()
        self.assertNetzBerieb(checkMsg=True, name="Netzbetrieb nach Unterspannung")
        self.fakeBMSNormalBetrieb()
        self.assertNetzLaden(checkMsg=False)
        self.assertError(checkMsg=False)

        self.printTestBeginnAndIncrTestNumber("Netzladen ein, egal welcher Akkustand")
        self.cycleSocAndAssert(1, 101, self.assertNetzLaden)




        self.localDeviceData
        self.logger.info(self, "Test abgeschlossen")
        raise Exception("Test abgeschlossen") 


    def threadBreak(self):
        pass