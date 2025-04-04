import time
import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from GridLoad.SocMeter import SocMeter
from GPIO.BasicUsbRelais import BasicUsbRelais
from Base.Supporter import Supporter
from Base.CEnum import CEnum
from Inverter.EffektaController import EffektaController
import Base
import subprocess
from enum import Enum


class PowerPlant(Worker):
    '''

    Used values, devices and classmethods:
    All required devices are blocking a startup until data received!
    required functions and constants:
            Inverter:
                    EffektaController.getCmdSwitchToBattery()                    returns cmd which is required to set inverter mode
                    EffektaController.getCmdSwitchToUtility()                    returns cmd which is required to set inverter mode
                    EffektaController.getCmdSwitchUtilityChargeOn()              returns cmd which is required to set inverter mode
                    EffektaController.getCmdSwitchUtilityChargeOff()             returns cmd which is required to set inverter mode
                    EffektaController.getCmdSwitchToUtilityWithUvDetection()     returns cmd which is required to set inverter mode
                    EffektaController.getCmdSwitchUtilityFastChargeOn()          returns cmd which is required to set inverter mode
                    EffektaController.getCombinedEffektaData()                   returns combined effekta data for given single effekta data
                            FloatingModeOr                                       bool, key in returnValue from getCombinedEffektaData()
                            OutputVoltageHighOr                                  bool, key in returnValue from getCombinedEffektaData()
                            OutputVoltageHighAnd                                 bool, key in returnValue from getCombinedEffektaData()
                            ErrorPresentOr                                       bool, key in returnValue from getCombinedEffektaData()
                            InputVoltageAnd                                      bool, key in returnValue from getCombinedEffektaData()
            SocMonitor:
                    SocMeter.InitAkkuProz                                        int, classVariable from SocMonitor normally -1    @todo evtl über ein bool nachdenken.


    required mqtt data:
            Inverter:
                    AcOutPower                                                   float, key in inverter data dict
            BMS:
                    BmsEntladeFreigabe                                           bool, key in BMS data dict
                    BmsMsgCounter                                                todo, implement! int, counter for required BMS msg to provide stuckAt errors. A new number triggers watchdog
            SocMonitor:
                    Prozent                                                      float, key in Soc data dict
    optional:
            BMS:
                    FullChargeRequired                                           bool, optional key in BMS data dict. On rising edge it will set switch FullChargeRequired to on and force SchaltschwelleAkkuXXX to 100%. No transfer to utility is triggerd,switch FullChargeRequired will be reseted if soc is 100%.
            Wetter:
                    Tag_0                                                        dict, key in wetter data dict
                        Sonnenstunden                                            int, key in Tag_0 dict
                    Tag_1                                                        dict, key in wetter data dict
                        Sonnenstunden                                            int, key in Tag_1 dict

    Data output from powerPlant:
            Inverter:
                    Commands to each given inverter. (managedEffektas)
            SocMonitor:
                    sends {"cmd":"resetSoc"} to SocMonitor if floatMode from inverter is set (rising edge)
            OutTopic:
                    {"BasicUsbRelais.gpioCmd":{"relWr": "0", "relPvAus": "1", "relNetzAus": "0"}}
                    {"BasicUsbRelais.gpioCmd":{"relPowerPlantWaiting": "0", "relPowerPlantRunning": "0", "RelNichtHeizen": "0", "RelLastAktiv": "0", "RelStufe1": "1", "RelStufe2": "0", "RelStufe3": "0"}}
    '''


    # @todo states noch sinnvoll benennen
    class tranferRelaisStates(CEnum):
        STATE_CHECK_INPUT_BEVORE_TRANSFER_TO_GRID   = 0
        STATE_SWITCH_TO_GRID                        = 1
        STATE_SWITCH_INVERTER_OFF                   = 2
        STATE_CHECK_OUTPUT_AFTER_INVERTER_OFF       = 3
        STATE_WAIT_FOR_INVERTER_MODE_REQ            = 4
        STATE_CHECK_OUTPUT_BEVORE_INVERTER_ON       = 5
        STATE_SWITCH_INVERTER_ON                    = 6
        STATE_CHECK_OUTPUT_AFTER_INVERTER_ON        = 7
        STATE_FINISCH_TRANSFER_TO_INVERTER          = 8
        STATE_CANCEL_TRANSFER_TO_INVERTER           = 9
        STATE_WAIT_FOR_GRID_MODE_REQ                = 10
        STATE_FORCE_TO_INVERTER                     = 11
        STATE_WAIT_FOR_NEW_INVERTER_DATA            = 12
        STATE_WAIT_FOR_GRID_AND_TIMEOUT             = 13

    _MIN_GOOD_WEATHER_HOURS = 6     # it's good weather if forecasted sun hours are more than this value
    _HUNDRED_PERCENT = 100          # just to make magic numbers more readable

    def setScriptValues(self, keyOrDict, valueInCaseOfKey = None):
        '''
        Every time a "self.scriptValues[]" is changed an mqtt message has to be sent out, so a centralized set method can also set the self.sendeMqtt flag

        @param keyOrDict            single key or dictionary containing several key/value pairs
        @param valueInCaseOfDict    if keyOrDict is not a dictionary an extra value has to be given
        '''
        def setScriptValue(key, value):
            '''
            Every time a "self.scriptValues[]" is changed an mqtt message has to be sent out, so a centralized set method can also set the self.sendeMqtt flag
            When key doesn't exist or when given value is different from current content new value is stored and mqtt flag is set to remember that an mqtt message has to be sent out

            @param key      key in self.scriptValues dictionary a value has to be set for
            @param value    the value that has to be set
            '''
            # when entry doesn't exist or when given value is different from current content set new value and remember that mqtt message has to be sent out
            if (key not in self.scriptValues) or (self.scriptValues[key] != value):
                self.scriptValues[key] = value
                self.sendeMqtt = True

        if isinstance(keyOrDict, str):
            # single key/value pair given
            setScriptValue(keyOrDict, valueInCaseOfKey)
        else:
            # dictionary with usually more than one key/value pair given
            for key in keyOrDict:
                setScriptValue(key, keyOrDict[key])


    def updateScriptValues(self, data : dict):
        '''
        Updates scriptValues dictionary with given data dictionary and remembers that new values have to be published

        @param data       dictionary containing new values for scriptValues dictionary
        '''
        self.scriptValues.update(data)
        self.sendeMqtt = True


    def passeSchaltschwellenAn(self):
        def setThresholds(gridThreshold : int, accuThreshold : int):
            '''
            Set threshold values with given thresholds if they are OK

            @param gridThreshold    threshold when the power will be taken from the grid
            @param accuThreshold    threshold when the power will be taken from the accumulator
            '''
            # grid threshold has to be smaller than accumulator threshold
            if gridThreshold < accuThreshold:
                # given thresholds different from already set ones?
                if (self.scriptValues["schaltschwelleNetz"] != gridThreshold) or (self.scriptValues["schaltschwelleAkku"] != accuThreshold):
                    self.setScriptValues({"schaltschwelleNetz" : gridThreshold, "schaltschwelleAkku" : accuThreshold})

        #SOC Schaltschwellen in Prozent
        self.setScriptValues({"schaltschwelleNetzLadenAus" : 12.0, "schaltschwelleNetzLadenEin" : 6.0, "MinSoc" : 10.0})
        # todo Automatisch ermitteln
        self.setScriptValues({"verbrauchNachtAkku" : 25.0, "verbrauchNachtNetz" : 3.0, "AkkuschutzAbschalten" : self.scriptValues["schaltschwelleAkkuSchlechtesWetter"] + 15.0})

        # self.scriptValues["AkkuschutzAbschalten"] must be between self.minAkkustandNacht() and 100%
        self.setScriptValues({
            "AkkuschutzAbschalten" : max(self.scriptValues["AkkuschutzAbschalten"], self.minAkkustandNacht()),   # ensure self.scriptValues["AkkuschutzAbschalten"] is not too small
            "AkkuschutzAbschalten" : min(self.scriptValues["AkkuschutzAbschalten"], self._HUNDRED_PERCENT)})     # ensure self.scriptValues["AkkuschutzAbschalten"] is not too large

        # Russia Mode hat Vorrang ansonsten entscheiden wir je nach Wetter (Akkuschutz)
        if self.scriptValues["RussiaMode"]:
            setThresholds(self.scriptValues["schaltschwelleNetzRussia"], self.scriptValues["schaltschwelleAkkuRussia"])
        elif self.scriptValues["Akkuschutz"]:
            setThresholds(self.scriptValues["schaltschwelleNetzSchlechtesWetter"], self.scriptValues["schaltschwelleAkkuSchlechtesWetter"])
        else:
            setThresholds(self.scriptValues["MinSoc"], self.scriptValues["schaltschwelleAkkuTollesWetter"])

        if self.configuration["resetFullchargeRequiredWithFloatmode"]:
            # if FullChargeRequired is used to reference soc monitor it is neccessary to reset this bit if floatMode from the inverter is detected
            if self.localDeviceData["combinedEffektaData"]["FloatingModeOr"]:
                self.setScriptValues("FullChargeRequired", False)
        elif self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] == self._HUNDRED_PERCENT:
            # if FullChargeRequired is used to balance battery and the bms or interface is able to send finally 100% soc. E.g. soc is 90% due balancing and 100% at the end of balancing.
            self.setScriptValues("FullChargeRequired", False)
        if self.scriptValues["FullChargeRequired"]:
            # we want to disable a switch to accumode until FullChargeRequired is resetet
            self.setScriptValues("schaltschwelleAkku", self._HUNDRED_PERCENT + 1)

        # ensure "schaltschwelleNetz" is at least as large as "MinSoc"
        self.setScriptValues("schaltschwelleNetz", max(self.scriptValues["schaltschwelleNetz"], self.scriptValues["MinSoc"]))

        # Wetter Sonnenstunden Schaltschwellen
        self.setScriptValues("wetterSchaltschwelleNetz", self._MIN_GOOD_WEATHER_HOURS)    # Einheit Sonnnenstunden

    def sendEffektaData(self, data, effektas):
        for inverter in effektas:
            self.mqttPublish(self.createInTopic(self.get_projectName() + "/" + inverter), data, globalPublish = False, enableEcho = False)

    def schalteAlleWrAufAkku(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToBattery(), effektas)
        self.setScriptValues({"WrMode" : self.AKKU_MODE, "WrNetzladen" : False})

    def schalteAlleWrAufNetzOhneNetzLaden(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtility(), effektas)
        self.setScriptValues({"WrMode" : self.GRID_MODE, "WrNetzladen" : False})

    def schalteAlleWrNetzLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOn(), effektas)
        self.setScriptValues({"WrMode" : self.GRID_MODE, "WrNetzladen" : True})

    def schalteAlleWrNetzLadenAus(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOff(), effektas)
        self.setScriptValues("WrNetzladen", False)

    def schalteAlleWrAufNetzMitNetzladen(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtilityWithUvDetection(), effektas)
        self.setScriptValues({"WrMode" : self.GRID_MODE, "WrNetzladen" : True})

    def schalteAlleWrNetzSchnellLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityFastChargeOn(), effektas)
        self.setScriptValues({"WrMode" : self.GRID_MODE, "WrNetzladen" : True})

    def resetSocMonitor(self):
        self.mqttPublish(self.createInTopic(self.createProjectTopic(self.configuration["socMonitorName"])), {"cmd":"resetSoc"}, globalPublish = False, enableEcho = False)

    def addCombinedEffektaDataToHomeautomation(self):
        # send Values to a homeAutomation to get there sensors
        unitDict = {}
        for key in self.localDeviceData["combinedEffektaData"]:
            unitDict[key] = "none"
        self.homeAutomation.mqttDiscoverySensor(self.localDeviceData["combinedEffektaData"], unitDict = unitDict, subTopic = "combinedEffektaData")
        self.sendCombinedEffektaData()

    def sendCombinedEffektaData(self):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + "combinedEffektaData", self.localDeviceData["combinedEffektaData"], globalPublish = True, enableEcho = False)

    def getCombinedEffektaData(self):
        dataList = {}
        for device in self.configuration["managedEffektas"]:
            if device in self.localDeviceData:
                dataList.update({device : self.localDeviceData[device]})
        return EffektaController.getCombinedEffektaData(dataList)

    def updateVariables(self):
        """
        update some variables in setableScriptValues
        AkkusSupply is True if all load is supplied from battery
        """
        self.setScriptValues("AkkuSupply", ((self.localDeviceData["combinedEffektaData"]["BatteryModeAnd"]) and (self.scriptValues["NetzRelais"] == self.INVERTER_MODE)))

    def manageLogicalCombinedEffektaData(self):
        """
        check logically combined Effekta data
        reset SocMonitor to 100% if floatMode is activ, and remember it
        send the data on topic ...out/combinedEffektaData if a new value arrived
        set and reset minBalanceTimeFinished to ensure that a load doesnt discharge too early and breaks balancing 
        """
        minBalanceTime = 60 * 30
        # create inverter data and if they differ from current ones publish them
        tempData = self.getCombinedEffektaData()
        if self.localDeviceData["combinedEffektaData"] != tempData:
            self.localDeviceData["combinedEffektaData"] = tempData
            self.sendCombinedEffektaData()

        # each time "FloatingModeOr" becomes True ("rising edge") a SOC reset message will be sent to set all SOCs to 100% 
        if self.localDeviceData["combinedEffektaData"]["FloatingModeOr"]:
            if not self.timerExists("timerFloatmode"):
                self.timer(name = "timerFloatmode", timeout = minBalanceTime)
            # the boolean ensures that the SOC reset is only sent once when inverters are in float mode and is only sent again when float mode has been left and entered again
            if not self.ResetSocSent:
                self.resetSocMonitor()                                          # send SOC reset
                self.setScriptValues("Error", False)                            # clear error
                self.ResetSocSent = True                                        # remember SOC reset has been sent
        else:
            self.ResetSocSent = False                   # float mode left, so ensure SOC reset will be sent again when float mode is entered the next time

        now = datetime.datetime.now()
        if self.timerExists("timerFloatmode"):
            self.localDeviceData["minBalanceTimeFinished"] = self.localDeviceData["minBalanceTimeFinished"] or self.timer(name = "timerFloatmode", timeout = minBalanceTime)
            if now.hour == 23:
                self.timer(name = "timerFloatmode", remove = True)
                self.localDeviceData["minBalanceTimeFinished"] = False

    def getInputValueByName(self, inputName : str):
        '''
        Searches given inputName in all inputs devices
        
        @param inputName        name of the input(s) to be searched
        
        @return    True in case given input could be found and its value was "1", if the value could have been found more than once return value will be only True if all found ones are "1", in all other cases False is given back
        '''
        allValuesOne = False
        found = False
        for device in self.configuration["inputs"]:
            if inputName in self.localDeviceData[device]["inputs"]:
                if found:
                    allValuesOne &= (int(self.localDeviceData[device]["inputs"][inputName], base = 10))    # only True when all found values are 1
                else:
                    allValuesOne |= (int(self.localDeviceData[device]["inputs"][inputName], base = 10))    # only True when all found values are 1
                found = True    # value at least found once
        return found and allValuesOne

    def modifyRelaisData(self, relayStates = None, expectedStates = None) -> bool:
        '''
        Sets relay output values and publishes new states
        If check values have been given the relay states will be checked before they will be changed, it's not necessary to give all existing relays but only given ones will be checked, the others will be ignored

        @param relayStates          new values the relays should be switched to
        @param expectedStates       values the relays should already be set to before any given relayStates are set
                                    values will be set to expected state if current state is different

        @return                     True in case all given checks are successful (what is the case if none has been given), False if at least one real state differs from expected state
        '''
        checkResult = True          # used as return value, will be set to False if any "expect compare" fails
        contentChanged = False      # if set to True an update message will be published

        # try to search any relay not in expected state
        if expectedStates is not None:
            for relay in expectedStates:
                if self.localRelaisData[BasicUsbRelais.gpioCmd][relay] != expectedStates[relay]:
                    checkResult = False
                    self.logger.error(self, f"Relay {relay} is in state {self.localRelaisData[BasicUsbRelais.gpioCmd][relay]} but expected state is {expectedStates[relay]}, callstack: {Supporter.getCallStack()}")
                    self.localRelaisData[BasicUsbRelais.gpioCmd][relay] = expectedStates[relay]
                    contentChanged = True

        # if relay states have been given update current values and ensure a message is published (even if old and new values are identically)
        if relayStates is not None:
            self.localRelaisData[BasicUsbRelais.gpioCmd].update(relayStates)
            contentChanged = True

        # if any value has been changed publish an update message 
        if contentChanged:
            self.publishRelaisData(self.localRelaisData)

        return checkResult

    def initTransferRelais(self):
        # subscribe global to in topic to get PowerSaveMode
        self.aufNetzSchaltenErlaubt = True
        self.aufPvSchaltenErlaubt = True
        self.errorTimerFinished = False
        self.GridTransferCounter = 0
        self.localRelaisData = {
            BasicUsbRelais.gpioCmd : {
                self.REL_NETZ_AUS : "unknown",      # initially set all relay states to "unknown"
                self.REL_PV_AUS   : "unknown",
                self.REL_WR_1     : "unknown"
            }
        }
        self.modifyRelaisData(
            {
                self.REL_NETZ_AUS : self.AUS,               # initially all relays are OFF: - grid is enabled
                self.REL_PV_AUS   : self.REL_PV_AUS_open,   #                               - inverters are enabled
                self.REL_WR_1     : self.AUS                #                               - inverter output voltages are disabled
            },
            expectedStates = {}                 # no expected states during initialization
        )
        self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_INVERTER_MODE_REQ
        self.setScriptValues("NetzRelais", self.GRID_MODE)
        # todo auf den tatsächlichen zustand des schützes aufsynchronisieren

    def manageUtilityRelais(self):
        '''
        ====================================================================================================
        startup                  || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        -------------------------++--------------+------------+----------++------------------------------------
                                 || OFF          | CLOSED     | OFF      || inverters are off, grid is active because hardware reasons but will be swich over to inverter mode whenever grid voltage is lost
        ====================================================================================================

        ====================================================================================================
        schalteRelaisAufInverter || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        -------------------------++--------------+------------+----------++------------------------------------
        initially                || OFF          | CLOSED     | OFF      || = grid mode
        STATE_0                  || OFF          | OPEN   <<< | ON  <<<  || disable inverters, enable inverters output voltages, this prevents the system from switching over to inverter mode
        STATE_2                  || OFF          | CLOSED <<< | ON       || as soon as inverter output voltages are stable switch utility relay over to inverter mode
        ====================================================================================================

        ====================================================================================================
        schalteRelaisAufInverter || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        error case               ||              |            |          ||
        -------------------------++--------------+------------+----------++------------------------------------
        initially                || OFF          | CLOSED     | OFF      || = grid mode
        STATE_0                  || OFF          | OPEN   <<< | ON  <<<  || disable inverters, enable inverters output voltages, this prevents the system from switching over to inverter mode
        STATE_1                  || OFF          | OPEN       | OFF <<<  || disable inverter output voltages again since at least one inverter output voltage hasn't ever seen
        STATE_3                  || OFF          | CLOSED <<< | OFF      || back in "startup" state because of output voltage error
        ====================================================================================================

        ====================================================================================================
        schalteRelaisAufNetz     || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        -------------------------++--------------+------------+----------++------------------------------------
        initially                || OFF          | CLOSED     | ON       || = inverter mode
        STATE_0                  || OFF          | OPEN   <<< | ON       || disable inverters what leads to automatic back switch to grid mode of the utility relay
        STATE_1                  || OFF          | OPEN       | OFF <<<  || switch inverter output voltages off now
        STATE_2                  || OFF          | CLOSED <<< | OFF      || back in "startup" state
        ====================================================================================================
        '''
        # Init some timouts and constants
        minGridTime                 = 60*5
        errorMessageTimer           = 60*10
        parameterSetTimer           = 30
        outputVoltageLowTimer       = 60*10
        inverterErrorResponseTime   = 80
        acOutTimeout                = 100
        maxGridTransfersPerDay      = 2
        debug = False

        # for debugging:
        #minGridTime                 = 15
        #parameterSetTimer           = 5
        #outputVoltageLowTimer       = 20
        #maxGridTransfersPerDay      = 3
        #debug = True

        def switchTransferRelais(deciredMode, forceToState = None):
            if forceToState is not None:
                self.tranferRelaisState = forceToState

            # first of all ensure that all inverters see their input voltages, otherwise a switch to the grid doesn't make any sense
            if self.tranferRelaisState == self.tranferRelaisStates.STATE_CHECK_INPUT_BEVORE_TRANSFER_TO_GRID:
                stateMode = self.TRANSFER_TO_NETZ
                if not self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"]:
                    if self.timer(name = "errorMessageTimer", timeout = errorMessageTimer, firstTimeTrue = True, removeOnTimeout = True):
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Keine Netzversorgung vorhanden!")
                else:
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_SWITCH_TO_GRID
                # if inputvoltage is not present we can leave this state and force to inverter.
                # Either inverter is already on, so a force will not change anything, or there is initial no grid and we want to switch inverter on
                # Without this check we might get stuck here without grid
                if deciredMode == self.INVERTER_MODE:
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_FORCE_TO_INVERTER
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_SWITCH_TO_GRID:
                stateMode = self.TRANSFER_TO_NETZ
                self.tranferRelaisState = self.tranferRelaisStates.STATE_SWITCH_INVERTER_OFF
                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf Netz.")
                self.modifyRelaisData(
                    {
                        self.REL_PV_AUS   : self.REL_PV_AUS_open,       # inverters get disabled now
                    },
                    expectedStates = {
                        self.REL_NETZ_AUS : self.AUS,
                        self.REL_PV_AUS   : self.REL_PV_AUS_closed,
                        self.REL_WR_1     : self.EIN,
                    }
                )
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_SWITCH_INVERTER_OFF:
                stateMode = self.TRANSFER_TO_NETZ
                # @todo Wendeschütz lesen und timer erst starten, wenn laut Wendeschütz Umschaltung durchgeführt wurde

                # warten bis Parameter geschrieben sind, wir wollen den Inverter nicht währendessen abschalten
                if self.timer(name = "parameterSetTimer", timeout = parameterSetTimer, removeOnTimeout = True):
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_CHECK_OUTPUT_AFTER_INVERTER_OFF
                    self.modifyRelaisData(
                        {
                            self.REL_WR_1     : self.AUS,       # now switch inverter output voltages off
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_CHECK_OUTPUT_AFTER_INVERTER_OFF:
                stateMode = self.GRID_MODE
                # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                if self.timer(name = "outputVoltageLowTimer", timeout = outputVoltageLowTimer, removeOnTimeout = True):
                    if self.localDeviceData["combinedEffektaData"]["OutputVoltageHighOr"]:
                        # Durch das ruecksetzten von PowersaveMode schalten wir als nächstes wieder zurück auf PV.
                        # Wir wollen im Fehlerfall keinen inkonsistenten Schaltzustand der Anlage darum schalten wir die Umrichter nicht aus.
                        self.setScriptValues("PowerSaveMode", False)
                        # @todo nachdenken was hier sinnvoll ist. Momentan wird wieder zurück auf inverter geschaltet wenn kein Fehler am Inverter anliegt
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Wechselrichter konnte nicht abgeschaltet werden. Er hat nach Wartezeit immer noch Spannung am Ausgang! Die Automatische Netzumschaltung wurde deaktiviert.")
                        # Die Wechselrichter lassen sich nicht ausschalten, wir schalten wieder auf inverter
                        self.tranferRelaisState = self.tranferRelaisStates.STATE_SWITCH_INVERTER_ON
                    else:
                        self.modifyRelaisData(
                            {
                                self.REL_PV_AUS   : self.REL_PV_AUS_closed,
                            },
                            expectedStates = {
                                self.REL_NETZ_AUS : self.AUS,
                                self.REL_PV_AUS   : self.REL_PV_AUS_open,
                                self.REL_WR_1     : self.AUS,
                            }
                        )
                        # kurz warten damit das zurücklesen nicht zu schnell geht
                        time.sleep(0.5)     # @todo gruselig, sollte durch Timer ersetzt werden!!!

                        self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_INVERTER_MODE_REQ

                    self.GridTransferCounter += 1

                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf Netz.")
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_WAIT_FOR_INVERTER_MODE_REQ:
                stateMode = self.GRID_MODE
                if (deciredMode == self.INVERTER_MODE) and self.aufPvSchaltenErlaubt:
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_CHECK_OUTPUT_BEVORE_INVERTER_ON
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_CHECK_OUTPUT_BEVORE_INVERTER_ON:
                stateMode = self.TRANSFER_TO_INVERTER
                # ensure that no inverter sees any output voltage, otherwise there is sth. wrong
                if self.localDeviceData["combinedEffektaData"]["OutputVoltageHighOr"] and not debug:
                    self.modifyRelaisData(
                        # all these states are already expected but sth. is wrong and inverter output voltages are on, so try to switch off again
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_closed,
                            self.REL_WR_1     : self.AUS,       # this should lead to a switch over to grid mode
                        }
                    )
                    if self.timer(name = "errorMessageTimer", timeout = errorMessageTimer, firstTimeTrue = True, removeOnTimeout = True):
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Output liefert bereits Spannung!")
                    # @todo auch hier kommen wir ggf. nie wieder raus, dann doch besser gezielt beenden!
                # warten bis Parameter geschrieben sind
                else:
                    if debug:
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Debug! No OutputVoltage checked!")
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_SWITCH_INVERTER_ON
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_SWITCH_INVERTER_ON:
                stateMode = self.TRANSFER_TO_INVERTER
                # If grid is down we want to switch on immediately the inverters else we wait for writing all parameters ensure a start with battery Mode
                if not self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"] or self.timer(name = "parameterSetTimer", timeout = parameterSetTimer, removeOnTimeout = True):
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf Inverter.")
                    # grid mode has to be active, inverter mode has to be inactive, switch on inverter output voltages
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,   # disable inverters, stay in grid mode
                            self.REL_WR_1     : self.EIN,               # enable inverter output voltages
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,
                            self.REL_WR_1     : self.AUS,
                        }
                    )
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_CHECK_OUTPUT_AFTER_INVERTER_ON
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_CHECK_OUTPUT_AFTER_INVERTER_ON:
                stateMode = self.TRANSFER_TO_INVERTER
                if self.timer(name = "timeoutAcOut", timeout = acOutTimeout, removeOnTimeout = True):                                # wait until inverter output voltages are ON and stable
                    self.setScriptValues("PowerSaveMode", False)        # Wir schalten die Funktion aus
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Wartezeit zu lange, keine Ausgangsspannung am WR erkannt, automatische Netzumschaltung deaktiviert.")
                    self.modifyRelaisData(
                        {
                            self.REL_WR_1     : self.AUS,       # disable inverter output voltages again since there wasn't detected any output voltages in time
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
                    # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_CANCEL_TRANSFER_TO_INVERTER
                elif self.localDeviceData["combinedEffektaData"]["OutputVoltageHighAnd"] == True:
                    self.timer(name = "timeoutAcOut", remove = True)    # timer hasn't timed out yet, so removeOnTimeout didn't get active, therefore, the timer has to be removed manually
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_FINISCH_TRANSFER_TO_INVERTER
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_FINISCH_TRANSFER_TO_INVERTER:
                stateMode = self.INVERTER_MODE
                if self.timer(name = "waitForOutputVoltage", timeout = 10, removeOnTimeout = True):
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.REL_PV_AUS_closed,       # enable inverters what makes utility relay switch over to inverter mode since inverter output voltages are up
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_GRID_MODE_REQ
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf Inverter.")
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_CANCEL_TRANSFER_TO_INVERTER:
                stateMode = self.GRID_MODE
                # Abbruch des Schaltvorgangs weil keine Outputvoltage erkannt wurde.
                if self.timer(name = "waitForOutputVoltage", timeout = outputVoltageLowTimer, removeOnTimeout = True):
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.REL_PV_AUS_closed,       # enable inverters what makes utility relay stay in grid mode since inverter output voltages are down
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.REL_PV_AUS_open,
                            self.REL_WR_1     : self.AUS,
                        }
                    )
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_INVERTER_MODE_REQ
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Umschaltung auf Inverter ist wegen fehlender Ausgangsspannung am WR fehlgeschlagen und steht jetzt wieder auf Netz.")
                    self.aufPvSchaltenErlaubt = False
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_WAIT_FOR_GRID_MODE_REQ:
                stateMode = self.INVERTER_MODE
                if (deciredMode == self.GRID_MODE) and self.aufNetzSchaltenErlaubt:
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_CHECK_INPUT_BEVORE_TRANSFER_TO_GRID
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_FORCE_TO_INVERTER:
                # Force relais to InverterMode, after minGridTime it is allowed to switch to grid again
                stateMode = self.INVERTER_MODE
                self.modifyRelaisData(
                    {
                        self.REL_NETZ_AUS : self.AUS,
                        self.REL_PV_AUS   : self.REL_PV_AUS_closed,
                        self.REL_WR_1     : self.EIN,           # enable inverters what makes utility relay stay in grid mode since inverter output voltages are down
                    },
                )
                # todo Parameter ??? Diese werden normalerweise vom threadMethod geschrieben
                # die Funktion self.schalteAlleWrAufAkku(self.configuration["managedEffektas"]) macht das
                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung hat automatisch auf Inverter geschaltet. Netzausfall.")
                self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_NEW_INVERTER_DATA
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_WAIT_FOR_NEW_INVERTER_DATA:
                stateMode = self.INVERTER_MODE
                if self.timer(name = "readParameterTimer", timeout = parameterSetTimer, removeOnTimeout = True):
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_GRID_AND_TIMEOUT
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung wartet auf Netzrückkehr.")
            elif self.tranferRelaisState == self.tranferRelaisStates.STATE_WAIT_FOR_GRID_AND_TIMEOUT:
                stateMode = self.INVERTER_MODE
                if self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"] and self.timer(name = "minGridTime", timeout = minGridTime, removeOnTimeout = True):
                    self.tranferRelaisState = self.tranferRelaisStates.STATE_WAIT_FOR_GRID_MODE_REQ
                # Reset timer if grid was available for a short time
                if not self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"] and self.timerExists("minGridTime"):
                    self.timerRemove("minGridTime")

            # Status des Netzrelais in scriptValues übertragen damit er auch gesendet wird
            self.setScriptValues("NetzRelais", stateMode)


        # @todo Netzausfallerkennung im worker ist noch nicht vorhanden (Parameter!!)

        # Die Hardware des Wendeschützes und die ZusatzRelais schalten automatisch auf Inverter (und starten diese auch) wenn das Netz ausfällt
        # Wir prüfen das hier und ziehen mit STATE_FORCE_TO_INVERTER den internen State auf INVERTER_MODE 
        if self.getInputValueByName("inverterActive") and self.scriptValues["NetzRelais"] == self.GRID_MODE:
            switchTransferRelais(self.INVERTER_MODE, self.tranferRelaisStates.STATE_FORCE_TO_INVERTER)

        if self.localDeviceData["combinedEffektaData"]["ErrorPresentOr"] == False:
            # only if timer exists errorTimerFinished can be True
            if self.timerExists("ErrorTimer"):
                self.timer(name = "ErrorTimer", remove = True)
                self.errorTimerFinished = False

            if self.GridTransferCounter >= maxGridTransfersPerDay:
                self.aufNetzSchaltenErlaubt = False

            # each day at 8 o'clock PM some variables have to be reset
            if self.timer(name = "DailyResetTimer", timeout = 60 * 60 * 24, startTime = Supporter.getTimeOfToday(hour = 20)):
                self.aufNetzSchaltenErlaubt = True
                self.GridTransferCounter = 0
                self.aufPvSchaltenErlaubt = True

            if self.scriptValues["PowerSaveMode"] == True:
                # worker switches between AKKU_MODE and GRID_MODE and both modes can be handled with TransferRelais INVERTER_MODE. 
                # so AKKU_MODE is mapped to INVERTER_MODE and GRID_MODE is GRID_MODE
                if self.scriptValues["WrMode"] == self.AKKU_MODE:
                    switchTransferRelais(self.INVERTER_MODE)
                else:
                    switchTransferRelais(self.scriptValues["WrMode"])
            else: # Powersave off
                # Wir resetten die Verriegelung hier auch, damit man durch aus und einschalten von PowerSaveMode das Umschalten auf Netz wieder frei gibt.
                self.aufNetzSchaltenErlaubt = True
                self.GridTransferCounter = 0
                switchTransferRelais(self.INVERTER_MODE)
        else: # Fehler vom Inverter
            # wir erlauben das umschalten auf netz damit die anlage auch ummschalten kann
            self.aufNetzSchaltenErlaubt = True

            # Wenn ein Fehler 80s ansteht, dann werden wir aktiv und schalten auf Netz um
            if self.errorTimerFinished:
                switchTransferRelais(self.GRID_MODE)
            elif self.timer(name = "ErrorTimer", timeout = inverterErrorResponseTime):
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Fehler am Inverter erkannt. Wir schalten auf Netz.")
                    # todo: wenn der fehler wieder weg ist nach dem umschalten auf Netz und abschlten der inverter, dann fallen wir in den if zweig und die Netzumschaltung schaltet wieder. Es könnte ein toggeln entstehen.
                    self.errorTimerFinished = True


    def publishRelaisData(self, relaisData : dict):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), relaisData, globalPublish = False, enableEcho = False)

    def modifyExcessRelaisData(self, relais : str, value : str, sendValue = False):
        '''
        Sets power relay state to given value, publish new values and gives information back if value has been changed or not
        @param relais        relay it's value has to be changed
        @param value         new value for given relay
        @param sendValue     if True the relay values will be published
        
        @return        True if old value was different form given one, otherwise False
        '''
        oldValue = None
        if relais in self.localPowerRelaisData[BasicUsbRelais.gpioCmd]:
            oldValue = self.localPowerRelaisData[BasicUsbRelais.gpioCmd][relais]
        self.localPowerRelaisData[BasicUsbRelais.gpioCmd][relais] = value

        if sendValue:
            self.publishRelaisData(self.localPowerRelaisData)

        return oldValue != value

    def initExcessPower(self):
        self.relStufe = "RelStufe"
        self.stufe1 = self.relStufe + "1"
        self.stufe2 = self.relStufe + "2"
        self.stufe3 = self.relStufe + "3"
        self.relNichtHeizen = "RelNichtHeizen"
        self.relLastAktiv = "RelLastAktiv"
        self.localPowerRelaisData = {BasicUsbRelais.gpioCmd:{}}
        #self.localPowerRelaisData = {BasicUsbRelais.gpioCmd:{self.stufe1: "unknown", self.stufe2: "unknown", self.stufe3: "unknown", self.relNichtHeizen: "unknown"}}
        self.modifyExcessRelaisData(self.stufe1, self.AUS)
        self.modifyExcessRelaisData(self.stufe2, self.AUS)
        self.modifyExcessRelaisData(self.stufe3, self.AUS)
        self.modifyExcessRelaisData(self.relLastAktiv, self.AUS)
        self.modifyExcessRelaisData(self.relNichtHeizen, self.AUS, True)
        self.setScriptValues("Load", 0)
        self.localLoad = 0
        self.nichtHeizen = self.AUS

    def manageExcessPower(self):
        # if we have excess power we manage in this funktion a 3 stage regulation appending on soc. If the power is to high we switch off individual load RelStufe 1..3 for L1..3. Wiring have to be correctly!
        # we also manage a output which can block a heater if we calculate enougth power for this day (weather)

        #  'WrEffektaWest': {'Netzspannung': 231, 'AcOutSpannung': 231.6, 'AcOutPower': 0, 'PvPower': 0, 'BattCharge': 0, 'BattDischarge': 0, 'ActualMode': 'B', 'DailyProduction': 0.0, 'CompleteProduction': 0, 'BattCapacity': 30, 'De 

        relayThresholds = sorted([96, 97, 98])                          # three thresholds means three supported relays, sorted because they are needed in ascending order!!!
        relayNames      = (self.stufe1, self.stufe2, self.stufe3)       # names of the relays to be switched off at the given thresholds
        rangeMaximum    = min(len(relayThresholds), len(relayNames))    # not more relays are supported than thresholds or relay names have been given

        # remember all inverters that are locked because of overload
        inverterLocked = []

        # set timers and switch off load if power of a inverter is too high
        for inverterIndex, inverter in enumerate(self.configuration["managedEffektas"]):
            if (self.localDeviceData[inverter]["AcOutPower"] > 2500) or (self.localDeviceData[inverter]["ActualMode"] != "B"):
                self.timer(f"overloadedInverter{inverterIndex}", 5 * 60, reSetup = True)    # currently power delivery of this inverter is too high
            inverterLocked.append((self.timerExists(f"overloadedInverter{inverterIndex}") is not None) and (not self.timer(f"overloadedInverter{inverterIndex}", removeOnTimeout = True)))

        # auto control enabled?
        if self.scriptValues["AutoLoadControl"]:
            now = datetime.datetime.now()

            # calculate heater disable relay
            if now.hour < self.configuration["HeaterWeatherControlledTime"] and not self.wetterPrognoseHeuteSchlecht(self.scriptValues["wetterSchaltschwelleHeizung"]):
                self.nichtHeizen = self.EIN
            else:
                self.nichtHeizen = self.AUS

            # calculate power stage appending on SOC
            if (self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] == 100) and self.localDeviceData["minBalanceTimeFinished"] and self.scriptValues["AkkuSupply"]:
                # all available/supported relays should be switched ON if 100% has been reached
                self.localLoad = rangeMaximum
            else:
                # switch to lower levels only, never switch up here!
                for loadIndex in range(0, rangeMaximum):
                    if (self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= relayThresholds[loadIndex]) and (self.localLoad > loadIndex):
                        self.localLoad = loadIndex
                        break   # correct load index found so leave for-loop
        else:
            # auto load control disabled, switch all heaters OFF
            self.localLoad = 0
            self.nichtHeizen = self.AUS

        updateRelaisTimerChanged = False

        # iterate over all relays and switch OFF not needed and not supported ones
        activeLoads = 0   # count activated loads
        for loadIndex in range(0, len(relayNames)):
            if (activeLoads < self.localLoad) and (loadIndex < rangeMaximum) and (loadIndex < len(inverterLocked)) and (not inverterLocked[loadIndex]):
                # more relays need to be switched ON
                # more relays available to be switched ON
                # more inverters are available so their referring relays can be switched ON
                # current inverter is not locked because of overload
                # -> then switch the referring relay ON
                updateRelaisTimerChanged = updateRelaisTimerChanged or self.modifyExcessRelaisData(relayNames[loadIndex], self.EIN)
                activeLoads += 1  # one more load activated
            else:
                # in all other cases switch referring relay OFF (relay must exist since we iterate over given relay names)
                updateRelaisTimerChanged = updateRelaisTimerChanged or self.modifyExcessRelaisData(relayNames[loadIndex], self.AUS)

        updateRelaisTimerChanged = updateRelaisTimerChanged or self.modifyExcessRelaisData(self.relNichtHeizen, self.nichtHeizen)

        # if one inverter is not locked and local load > 0
        if self.localLoad > 0 and (not all(inverterLocked)):
            updateRelaisTimerChanged = updateRelaisTimerChanged or self.modifyExcessRelaisData(self.relLastAktiv, self.EIN)
        else:
            updateRelaisTimerChanged = updateRelaisTimerChanged or self.modifyExcessRelaisData(self.relLastAktiv, self.AUS)

        # send new relay values and update scriptValues
        if updateRelaisTimerChanged:
            self.setScriptValues("Load", self.localLoad)
            self.publishRelaisData(self.localPowerRelaisData)


    def wetterPrognoseSchlecht(self, day : str, switchingThreshold : int) -> bool:
        result = False
        if day in self.localDeviceData[self.configuration["weatherName"]]:
            if self.localDeviceData[self.configuration["weatherName"]][day] != None:
                if self.localDeviceData[self.configuration["weatherName"]][day]["Sonnenstunden"] <= switchingThreshold:
                    result = True
            elif self.timer(name = "timerErrorPrint", timeout = 600, firstTimeTrue = True):
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")
        return result


    def wetterPrognoseMorgenSchlecht(self, switchingThreshold : int) -> bool:
        # Wir wollen abschätzen ob wir auf Netz schalten müssen dazu soll abends geprüft werden ob noch genug energie für die Nacht zur verfügung steht
        # Dazu wird geprüft wie das Wetter (Sonnenstunden) am nächsten Tag ist und dementsprechend früher oder später umgeschaltet.
        # Wenn das Wetter am nächsten Tag schlecht ist macht es keinen Sinn den Akku leer zu machen und dann im Falle einer Unterspannung vom Netz laden zu müssen.
        # Die Prüfung ist nur Abends aktiv da man unter Tags eine andere Logik haben möchte.
        # In der Sommerzeit löst now.hour = 17 um 18 Uhr aus, In der Winterzeit dann um 17 Uhr
        return self.wetterPrognoseSchlecht("Tag_1", switchingThreshold)

    def wetterPrognoseHeuteSchlecht(self, switchingThreshold : int) -> bool:
        return self.wetterPrognoseSchlecht("Tag_0", switchingThreshold)


    def minAkkustandNacht(self) -> float:
        return self.scriptValues["verbrauchNachtAkku"] + self.scriptValues["MinSoc"]

    def akkuStandAusreichend(self) -> bool:
        return self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.minAkkustandNacht()

    def initInverter(self):
        if self.configuration["initModeEffekta"] == self.AUTO_MODE:
            if self.localDeviceData["AutoInitRequired"]:
                self.autoInitInverter()
        elif self.configuration["initModeEffekta"] == self.AKKU_MODE:
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.setScriptValues("AutoMode", False)
        elif self.configuration["initModeEffekta"] == self.GRID_MODE:
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.setScriptValues("AutoMode", False)
        else:
            raise Exception(f"Unknown initModeEffekta [{self.configuration['initModeEffekta']}] given! Check configurationFile!")

    def strFromLoggerLevel(self, msgType):
        # convert LOGGER.INFO -> "info" and concat it to topic
        msgTypeSegment = str(msgType)
        msgTypeSegment = msgTypeSegment.split(".")[1]
        return msgTypeSegment.lower()

    def publishAndLog(self, msgType, msg, logMessage : bool = True):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + self.strFromLoggerLevel(msgType), {self.strFromLoggerLevel(msgType) : msg}, globalPublish = True, enableEcho = False)
        # @todo sende an Messenger
        if logMessage:
            self.logger.message(msgType, self, msg)

    def autoInitInverter(self):
        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] == SocMeter.InitAkkuProz:
            self.publishAndLog(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz mit Laden. SOC == InitWert")
            self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
        elif 0 <= self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] < self.scriptValues["schaltschwelleNetzLadenAus"]:
            self.publishAndLog(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz mit Laden")
            self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
        elif self.scriptValues["schaltschwelleNetzLadenAus"] <= self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] < self.scriptValues["schaltschwelleNetzSchlechtesWetter"]:
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            self.publishAndLog(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz ohne Laden")
        elif self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleAkkuSchlechtesWetter"]:
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            self.publishAndLog(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Akku")

    def checkForKeyAndCheckRisingEdge(self, oldDataDict : dict, newMessageDict : dict, key) -> bool:
        return (key in oldDataDict) and (key in newMessageDict) and newMessageDict[key] and not oldDataDict[key]

    def handleMessage(self, message):
        """
        sort the incoming msg to the localDeviceData variable
        handle expectedDevicesPresent variable
        set setable values wich are received global
        """

        #if message["topic"].find("UsbRelaisWd") != -1:
        #    Supporter.debugPrint(f"{self.name} got message {message}", color = "GREEN")
        #    #{'topic': 'AccuControl/UsbRelaisWd1/out', 'global': False, 'content': {'inputs': {'Input3': '0', 'readbackGrid': '0', 'readbackInverter': '0', 'readbackSolarContactor': '0'}}}
        #    #{'topic': 'AccuControl/UsbRelaisWd2/out', 'global': False, 'content': {'inputs': {'Input0': '0', 'Input1': '0', 'Input2': '0', 'Input3': '0'}}}
        #    #"gridActive"
        #    #"inverterActive"

        # check if its our own out topic
        if self.createOutTopic(self.getObjectTopic()) in message["topic"]:
            # we use it and unsubscribe
            self.updateScriptValues(message["content"])
            self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))

            # timer didn't time out but we received a message from MQTT broker so remove the surely still existing timer
            if self.timerExists("timeoutMqtt"):
                self.timer(name = "timeoutMqtt", remove = True)

            self.localDeviceData["initialMqttTimeout"] = True

            # we got our own data so we don't need to auto-initialize inverters
            self.localDeviceData["AutoInitRequired"] = False
        elif self.createInTopic(self.getObjectTopic()) in message["topic"]:
            # check if the incoming value is part of self.setableScriptValues and if true then take the new value
            for key in self.setableScriptValues:
                if key in message["content"]:
                    if type(self.scriptValues[key]) == float and type(message["content"][key]) == int:
                        message["content"][key] = float(message["content"][key])
                    if type(self.scriptValues[key]) == int and type(message["content"][key]) == float:
                        message["content"][key] = int(message["content"][key])
                    try:
                        if type(message["content"][key]) == type(self.scriptValues[key]):
                            self.setScriptValues(key, message["content"][key])
                        else:
                            self.logger.error(self, "Wrong datatype globally received.")
                    except Exception as ex:
                        self.logger.error(self, f"Wrong datatype globally received, exception: {ex}")

            if message["content"] in self.manualCommands:
                # if it is a dummy command. we do nothing
                if message["content"] != self.dummyCommand:
                    self.setScriptValues("AutoMode", False)
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Anlage wurde auf Manuell gestellt")
                    if message["content"] == "NetzSchnellLadenEin":
                        self.schalteAlleWrNetzSchnellLadenEin(self.configuration["managedEffektas"])
                    elif message["content"] == "NetzLadenEin":
                        self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
                    elif message["content"] == "NetzLadenAus":
                        self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])
                    elif message["content"] == "WrAufNetz":
                        self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                    elif message["content"] == "WrAufAkku":
                        self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
        else:
            # incoming msg is for other devices
            # check if a expected device sent a msg and store it
            for key in self.expectedDevices:
                if key in message["topic"]:
                    if key in self.localDeviceData: # Filter first run
                        # check FullChargeRequired from BMS for rising edge
                        if key == self.configuration["bmsName"] and self.checkForKeyAndCheckRisingEdge(self.localDeviceData[self.configuration["bmsName"]], message["content"], "FullChargeRequired"):
                            self.setScriptValues("FullChargeRequired", True)
                    else:
                        self.localDeviceData[key] = {}
                    # if a device sends partial data we have a problem if we copy the msg, so we update our dict instead
                    self.localDeviceData[key].update(message["content"])

            # check if an optional device sent a msg and store it
            for key in self.optionalDevices:
                if key in message["topic"]:
                    self.localDeviceData[key] = message["content"]

            # check if all expected devices sent data
            if not self.localDeviceData["expectedDevicesPresent"]:
                # set expectedDevicesPresent. If a device is not present we reset the value
                self.localDeviceData["expectedDevicesPresent"] = True
                # check if a expected device sent a msg and store it
                for key in self.expectedDevices:
                    # check if all devices are present
                    if not (key in self.localDeviceData):
                        self.localDeviceData["expectedDevicesPresent"] = False
                        break   # one missing device found, so stop searching
                if self.localDeviceData["expectedDevicesPresent"]:
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Starte PowerPlant!")

    def threadInitMethod(self):
        self.publishAndLog(Logger.LOG_LEVEL.INFO,  "---", logMessage = False)     # set initial value, don't log it!
        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "---", logMessage = False)     # set initial value, don't log it!

        self.tagsIncluded(["managedEffektas", "initModeEffekta", "socMonitorName", "bmsName"])
        self.tagsIncluded(["weatherName"], optional = True, default = "noWeatherConfigured")
        self.tagsIncluded(["HeaterWeatherControlledTime"], optional = True, default = 7)        # never heat before 7 o'clock in the morning
        self.tagsIncluded(["inputs"], optional = True, default = [])
        self.tagsIncluded(["resetFullchargeRequiredWithFloatmode"], optional = True, default = False)

        # if there was only one module given for inputs convert it to a list
        if type(self.configuration["inputs"]) != list:
            self.configuration["inputs"] = [self.configuration["inputs"]]

        # Threadnames we have to wait for an initial message. The worker needs this data.
        self.expectedDevices = []
        self.expectedDevices.append(self.configuration["socMonitorName"])
        self.expectedDevices.append(self.configuration["bmsName"])
        # add managedEffekta List, function getCombinedEffektaData needs this data
        self.expectedDevices += self.configuration["managedEffektas"]

        self.optionalDevices = []
        self.optionalDevices.append(self.configuration["weatherName"])
        self.optionalDevices += self.configuration["inputs"]

        # init some variables
        self.localDeviceData = {"expectedDevicesPresent": False, "initialMqttTimeout": False, "initialRelaisTimeout": False, "AutoInitRequired": True, "combinedEffektaData":{},"minBalanceTimeFinished": False, self.configuration["weatherName"]:{}}
        # init lists of direct set-able values, sensors or commands
        self.setableSlider = {"schaltschwelleAkkuTollesWetter":20.0, "schaltschwelleAkkuRussia":100.0, "schaltschwelleNetzRussia":80.0, "schaltschwelleAkkuSchlechtesWetter":45.0, "schaltschwelleNetzSchlechtesWetter":30.0, "wetterSchaltschwelleHeizung":9}
        self.niceNameSlider = {"schaltschwelleAkkuTollesWetter":"Akku gutes Wetter", "schaltschwelleAkkuRussia":"Akku USV", "schaltschwelleNetzRussia":"Netz USV", "schaltschwelleAkkuSchlechtesWetter":"Akku schlechtes Wetter", "schaltschwelleNetzSchlechtesWetter":"Netz schlechtes Wetter", "wetterSchaltschwelleHeizung":"Sonnenstunden nicht heizen"}
        self.setableSwitch = {"Akkuschutz":False, "RussiaMode": False, "PowerSaveMode" : False, "AutoMode": True, "FullChargeRequired": False, "AutoLoadControl": True}
        self.sensors = {"WrNetzladen":False, "Error":False, "AkkuSupply":False, "WrMode":"", "schaltschwelleAkku":100.0, "schaltschwelleNetz":20.0, "NetzRelais": "", "Load":0}
        self.manualCommands = ["NetzSchnellLadenEin", "NetzLadenEin", "NetzLadenAus", "WrAufNetz", "WrAufAkku"]
        self.dummyCommand = "NoCommand"
        self.manualCommands.append(self.dummyCommand)
        self.scriptValues = {}
        self.updateScriptValues(self.setableSlider)
        self.updateScriptValues(self.setableSwitch)
        self.updateScriptValues(self.sensors)
        self.setableScriptValues = []
        self.setableScriptValues += list(self.setableSlider.keys())
        self.setableScriptValues += list(self.setableSwitch.keys())
        self.startupInitialization = False
        self.EntladeFreigabeGesendet = False
        self.NetzLadenAusGesperrt = False
        self.ResetSocSent = False

        # init some constants
        self.AKKU_MODE     = "Akku"
        self.GRID_MODE     = "Netz"
        self.AUTO_MODE     = "Auto"
        self.INVERTER_MODE = "Inverter"
        self.TRANSFER_TO_INVERTER = "transferToInverter"
        self.TRANSFER_TO_NETZ     = "transferToNetz"
        self.REL_WR_1     = "relWr"
        self.REL_PV_AUS   = "relPvAus"
        self.REL_NETZ_AUS = "relNetzAus"
        self.EIN = BasicUsbRelais.REL_ON
        self.AUS = BasicUsbRelais.REL_OFF

        self.tagsIncluded(["REL_PV_AUS_NC"], optional = True, default = True)
        if self.configuration['REL_PV_AUS_NC'] == True:
            # "REL_PV_AUS_NC"
            self.REL_PV_AUS_closed = self.AUS
            self.REL_PV_AUS_open   = self.EIN
        else:
            # "REL_PV_AUS_NO"
            self.REL_PV_AUS_closed = self.EIN
            self.REL_PV_AUS_open   = self.AUS

        # init TransferRelais to switch all Relais to initial position
        self.initTransferRelais()

        self.initExcessPower()


        # subscribe global to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        # subscribe Global to get commands from extern
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)


        # local publish geht NUR an local subscriber
        # global publish geht NUR an global subscriber
        # ABER a global subscriber subscribed automatisch a local, somit geht global und local immer an alle global subscriber und local nur an de local

        for device in self.expectedDevices:
            self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(device)), globalSubscription = False)

        for device in self.optionalDevices:
            self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(device)), globalSubscription = False)

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self.sensors)
        self.homeAutomation.mqttDiscoverySelector(self.manualCommands, niceName = "Pv Cmd")
        self.homeAutomation.mqttDiscoveryInputNumberSlider(self.setableSlider, nameDict = self.niceNameSlider)
        self.homeAutomation.mqttDiscoverySwitch(self.setableSwitch)

        self.homeAutomation.mqttDiscoverySensor(sensors = [self.strFromLoggerLevel(Logger.LOG_LEVEL.INFO)], subTopic = self.strFromLoggerLevel(Logger.LOG_LEVEL.INFO))
        self.homeAutomation.mqttDiscoverySensor(sensors = [self.strFromLoggerLevel(Logger.LOG_LEVEL.ERROR)], subTopic = self.strFromLoggerLevel(Logger.LOG_LEVEL.ERROR))

        self.modifyExcessRelaisData("relPowerPlantRunning", self.AUS, True)
        self.modifyExcessRelaisData("relPowerPlantWaiting", self.EIN, True)

        # Test if file logging is working
        self.logger.info(self, "Test Log entry")
        self.logger.writeLogBufferToDisk(f"logfiles/test_error.log")

    def threadMethod(self):
        self.sendeMqtt = False

        ###Supporter.debugPrint(f"local device data: {self.localDeviceData['UsbRelaisWd1'] if 'UsbRelaisWd1' in self.localDeviceData else None}", color = "LIGHTYELLOW")

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)
            self.handleMessage(newMqttMessageDict)

        # give mosquitto 30 seconds time to send back any retained messages until we unsubscribe
        if (not self.localDeviceData["initialMqttTimeout"]) and self.timer(name = "timeoutMqtt", timeout = 30, removeOnTimeout = True):
            self.localDeviceData["initialMqttTimeout"] = True   # ensures that the previous "if" becomes True now since timer has already removed itself
            self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
            self.logger.info(self, "MQTT init timeout, no data received from MQTT broker, probably there wasn't any retained message.")

        # if all devices have sent their work data and timeout values for external MQTT data, the worker will be executed
        if self.localDeviceData["expectedDevicesPresent"] and self.localDeviceData["initialMqttTimeout"]:
            self.manageLogicalCombinedEffektaData()
            now = datetime.datetime.now()

            self.passeSchaltschwellenAn()

            self.manageExcessPower()
            self.updateVariables()

            # do some initialization during startup
            if not self.startupInitialization:
                self.startupInitialization = True        # do startup initialization only once
                self.addCombinedEffektaDataToHomeautomation()
                self.initInverter()
                # init TransferRelais a second Time to overwrite scriptValues["NetzRelais"] with the initial value. The initial MQTT msg maybe wrote last state to this key!
                self.initTransferRelais()
                self.modifyExcessRelaisData("relPowerPlantWaiting", self.AUS, True)

            # Wir prüfen als erstes ob die Freigabe vom BMS da ist und kein Akkustand Error vorliegt
            if self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"] and not self.scriptValues["Error"]:
                # Wir wollen erst prüfen ob das skript automatisch schalten soll.
                if self.scriptValues["AutoMode"]:
                    # todo self.setScriptValues("Akkuschutz", False) Über Wetter?? Was ist mit "Error: Ladestand weicht ab"
                    if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] > self.scriptValues["AkkuschutzAbschalten"]:
                        # above self.scriptValues["AkkuschutzAbschalten"] threshold then "Akkuschutz" is disabled
                        self.setScriptValues("Akkuschutz", False)

                    # Wir prüfen ob wir wegen zu wenig prognostiziertem Ertrag den Akkuschutz einschalten müssen. Der Akkuschutz schaltet auf einen höheren (einstellbar) SOC Bereich um.
                    if not self.scriptValues["Akkuschutz"]:
                        if self.wetterPrognoseMorgenSchlecht(self.scriptValues["wetterSchaltschwelleNetz"]) and (not self.akkuStandAusreichend()):
                            if (17 <= now.hour < 23) or ((12 <= now.hour < 23) and self.wetterPrognoseHeuteSchlecht(self.scriptValues["wetterSchaltschwelleNetz"])):
                                #self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                                self.setScriptValues("Akkuschutz", True)
                                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Sonnen Stunden < %ih -> schalte Akkuschutz ein." %self.scriptValues["wetterSchaltschwelleNetz"])

                    self.passeSchaltschwellenAn()

                    # behandeln vom Laden in RussiaMode (USV)
                    if self.scriptValues["RussiaMode"]:
                        self.NetzLadenAusGesperrt = True
                        if self.scriptValues["WrNetzladen"] == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= (self.scriptValues["schaltschwelleNetz"] - self.scriptValues["verbrauchNachtNetz"]):
                            self.schalteAlleWrNetzSchnellLadenEin(self.configuration["managedEffektas"])
                        if self.scriptValues["WrNetzladen"] == True and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleNetz"]:
                            self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])

                    # Umschalten auf Netz oder Akku je nach dem ob die Schaltschwellen gerissen wurden. Darauf achten dass Netz vorhanden ist
                    # self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"] = False
                    if self.scriptValues["WrMode"] == self.AKKU_MODE:
                        if (self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= self.scriptValues["schaltschwelleNetz"]) and self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"]:
                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.publishAndLog(Logger.LOG_LEVEL.INFO, "%iP erreicht -> schalte auf Netz." %self.scriptValues["schaltschwelleNetz"])
                    elif self.scriptValues["WrMode"] == self.GRID_MODE:
                        if (self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleAkku"]) or not self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"]:
                            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
                            self.NetzLadenAusGesperrt = False
                            if self.localDeviceData["combinedEffektaData"]["InputVoltageAnd"]:
                                self.publishAndLog(Logger.LOG_LEVEL.INFO, "%iP erreicht -> Schalte auf Akku"  %self.scriptValues["schaltschwelleAkku"])
                            else:
                                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Netzausfall erkannt -> Schalte auf Akku")
                    else:
                        # Wr Mode nicht bekannt
                        self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, f"WrMode [{self.scriptValues['WrMode']}] nicht bekannt! Schalte auf Netz")


                    # Wenn Akkuschutz an ist und die schaltschwelle NetzLadenEin erreicht ist, dann laden wir vom Netz
                    if (not self.scriptValues["WrNetzladen"]) and (self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= self.scriptValues["schaltschwelleNetzLadenEin"]):
                        self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
                        self.publishAndLog(Logger.LOG_LEVEL.INFO, "Schalte auf Netz mit laden")


                    # Wenn das Netz Laden durch eine Unterspannungserkennung eingeschaltet wurde schalten wir es aus wenn der Akku wieder 10% hat
                    if self.scriptValues["WrNetzladen"] and self.NetzLadenAusGesperrt == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleNetzLadenAus"]:
                        self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])
                        self.publishAndLog(Logger.LOG_LEVEL.INFO, "NetzLadenaus %iP erreicht -> schalte Laden aus." %self.scriptValues["schaltschwelleNetzLadenAus"])


                # Wenn das BMS die entladefreigabe wieder erteilt dann reseten wir EntladeFreigabeGesendet damit das nachste mal wieder gesendet wird
                self.EntladeFreigabeGesendet = False
            elif not self.EntladeFreigabeGesendet:
                self.EntladeFreigabeGesendet = True
                self.schalteAlleWrAufNetzMitNetzladen(self.configuration["managedEffektas"])
                # Falls der Akkustand zu hoch ist würde nach einer Abschaltung das Netzladen gleich wieder abgeschaltet werden das wollen wir verhindern
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, f'Schalte auf Netz mit laden. Trigger-> BMS: {not self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"]}, Error: {self.scriptValues["Error"]}')
                if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleNetzLadenAus"]:
                    # Wenn eine Unterspannnung SOC > schaltschwelleNetzLadenAus ausgelöst wurde dann stimmt mit dem SOC etwas nicht und wir wollen verhindern, dass die Ladung gleich wieder abgestellt wird
                    self.NetzLadenAusGesperrt = True
                    self.setScriptValues("Akkuschutz", True)
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, f'Ladestand fehlerhaft')
                # wir setzen einen error weil das nicht plausibel ist und wir hin und her schalten sollte die freigabe wieder kommen
                # wir wollen den Akku erst bis 100 P aufladen
                if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleAkkuTollesWetter"]:
                    self.setScriptValues("Error", True)
                    # Wir setzen den Error zurück wenn der Inverter auf Floatmode umschaltet. Wenn diese bereits gesetzt ist dann müssen wir das Skript beenden da der Error sonst gleich wieder zurück gesetzt werden würde
                    if self.localDeviceData["combinedEffektaData"]["FloatingModeOr"] == True:
                        raise Exception(f'SOC: {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}, EntladeFreigabe: {self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"]}, und FloatMode von Inverter aktiv! Unplausibel!') 
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, 'Error wurde gesetzt, reset bei vollem Akku. FloatMode.')
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, f'Unterspannung BMS bei {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}%')

            self.passeSchaltschwellenAn()

            # for the first 30 seconds after PowerPlant has been started the relay will not be switched, that suppresses unnecessary relay switching processes when PowerPlant is started several times, e.g. because of debugging reasons
            if not self.localDeviceData["initialRelaisTimeout"] and self.timer(name = "timeoutTransferRelais", timeout = 30, removeOnTimeout = True):
                self.localDeviceData["initialRelaisTimeout"] = True             # from now on this value will ensure that the previous "if" becomes True, since timer has already removed itself
                # All initial timers are finished now, so we switch on the relPowerPlantRunning relais
                self.modifyExcessRelaisData("relPowerPlantRunning", self.EIN, True)

            if self.localDeviceData["initialRelaisTimeout"]:
                self.manageUtilityRelais()

            # Do mqtt values have to be updated?
            if self.sendeMqtt:
                self.sendeMqtt = False
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.scriptValues, globalPublish = True, enableEcho = False)
        else:
            TIMEOUT = 3 * 60
            if self.timer(name = "timeoutExpectedDevices", timeout = TIMEOUT):
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Es haben sich nicht alle erwarteten Devices gemeldet!")

                for device in self.expectedDevices:
                    if not device in self.localDeviceData:
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, f"Device: {device} fehlt!")
                raise Exception(f"Some devices are missed after timeout of {TIMEOUT}s!")


    def threadBreak(self):
        time.sleep(0.2)

