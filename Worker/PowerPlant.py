import time
import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from GridLoad.SocMeter import SocMeter
from GPIO.BasicUsbRelais import BasicUsbRelais
from Base.Supporter import Supporter
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
                    EffektaController.getLinkedEffektaData()                     returns linked effekta data for given single effekta data
                            FloatingModeOr                                       bool, key in returnValue from getLinkedEffektaData()
                            OutputVoltageHighOr                                  bool, key in returnValue from getLinkedEffektaData()
                            OutputVoltageHighAnd                                 bool, key in returnValue from getLinkedEffektaData()
                            ErrorPresentOr                                       bool, key in returnValue from getLinkedEffektaData()
                            InputVoltageAnd                                      bool, key in returnValue from getLinkedEffektaData()
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
    '''


    # @todo states noch sinnvoll benennen
    class switchToGrid(Enum):
        STATE_0 = 0
        STATE_1 = 1
        STATE_2 = 2

    class switchToInverter(Enum):
        STATE_0 = 0
        STATE_1 = 1
        STATE_2 = 2
        STATE_3 = 3

    _MIN_GOOD_WEATHER_HOURS = 6     # it's good weather if forecasted sun hours are more than this value
    _HUNDRED_PERCENT = 100          # just to make magic numbers more readable

    def setSkriptValues(self, keyOrDict, valueInCaseOfKey = None):
        '''
        Every time a "self.scriptValues[]" is changed an mqtt message has to be sent out, so a centralized set method can also set the self.sendeMqtt flag

        @param keyOrDict            single key or dictionary containing several key/value pairs
        @param valueInCaseOfDict    in case of keyOrDict is not as dictionary a value has to be given
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
                    self.setSkriptValues({"schaltschwelleNetz" : gridThreshold, "schaltschwelleAkku" : accuThreshold})

        #SOC Schaltschwellen in Prozent
        self.setSkriptValues({"schaltschwelleNetzLadenAus" : 12.0, "schaltschwelleNetzLadenEin" : 6.0, "MinSoc" : 10.0})
        # todo Automatisch ermitteln
        self.setSkriptValues({"verbrauchNachtAkku" : 25.0, "verbrauchNachtNetz" : 3.0, "AkkuschutzAbschalten" : self.scriptValues["schaltschwelleAkkuSchlechtesWetter"] + 15.0})

        # self.scriptValues["AkkuschutzAbschalten"] must be between self.minAkkustandNacht() and 100%
        self.setSkriptValues({
            "AkkuschutzAbschalten" : max(self.scriptValues["AkkuschutzAbschalten"], self.minAkkustandNacht()),   # ensure self.scriptValues["AkkuschutzAbschalten"] is not too small
            "AkkuschutzAbschalten" : min(self.scriptValues["AkkuschutzAbschalten"], self._HUNDRED_PERCENT)})     # ensure self.scriptValues["AkkuschutzAbschalten"] is not too large

        # Russia Mode hat Vorrang ansonsten entscheiden wir je nach Wetter (Akkuschutz)
        if self.scriptValues["RussiaMode"]:
            setThresholds(self.scriptValues["schaltschwelleNetzRussia"], self.scriptValues["schaltschwelleAkkuRussia"])
        elif self.scriptValues["Akkuschutz"]:
            setThresholds(self.scriptValues["schaltschwelleNetzSchlechtesWetter"], self.scriptValues["schaltschwelleAkkuSchlechtesWetter"])
        else:
            setThresholds(self.scriptValues["MinSoc"], self.scriptValues["schaltschwelleAkkuTollesWetter"])

        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] == self._HUNDRED_PERCENT:
            self.setSkriptValues("FullChargeRequired", False)
        if self.scriptValues["FullChargeRequired"]:
            self.setSkriptValues("schaltschwelleAkku", self._HUNDRED_PERCENT)

        # ensure "schaltschwelleNetz" is at least as large as "MinSoc"
        self.setSkriptValues("schaltschwelleNetz", max(self.scriptValues["schaltschwelleNetz"], self.scriptValues["MinSoc"]))

        # Wetter Sonnenstunden Schaltschwellen
        self.setSkriptValues("wetterSchaltschwelleNetz", self._MIN_GOOD_WEATHER_HOURS)    # Einheit Sonnnenstunden

    def sendEffektaData(self, data, effektas):
        for inverter in effektas:
            self.mqttPublish(self.createInTopic(self.get_projectName() + "/" + inverter), data, globalPublish = False, enableEcho = False)

    def schalteAlleWrAufAkku(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToBattery(), effektas)
        self.setSkriptValues({"WrMode" : self.AKKU_MODE, "WrNetzladen" : False})

    def schalteAlleWrAufNetzOhneNetzLaden(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtility(), effektas)
        self.setSkriptValues({"WrMode" : self.NETZ_MODE, "WrNetzladen" : False})

    def schalteAlleWrNetzLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOn(), effektas)
        self.setSkriptValues({"WrMode" : self.NETZ_MODE, "WrNetzladen" : True})

    def schalteAlleWrNetzLadenAus(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOff(), effektas)
        self.setSkriptValues("WrNetzladen", False)

    def schalteAlleWrAufNetzMitNetzladen(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtilityWithUvDetection(), effektas)
        self.setSkriptValues({"WrMode" : self.NETZ_MODE, "WrNetzladen" : True})

    def schalteAlleWrNetzSchnellLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityFastChargeOn(), effektas)
        self.setSkriptValues({"WrMode" : self.NETZ_MODE, "WrNetzladen" : True})

    def resetSocMonitor(self):
        self.mqttPublish(self.createInTopic(self.createProjectTopic(self.configuration["socMonitorName"])), {"cmd":"resetSoc"}, globalPublish = False, enableEcho = False)

    def addLinkedEffektaDataToHomeautomation(self):
        # send Values to a homeAutomation to get there sensors
        unitDict = {}
        for key in self.localDeviceData["linkedEffektaData"]:
            unitDict[key] = "none"
        self.homeAutomation.mqttDiscoverySensor(self.localDeviceData["linkedEffektaData"], unitDict = unitDict, subTopic = "linkedEffektaData")
        self.sendLinkedEffektaData()

    def sendLinkedEffektaData(self):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + "linkedEffektaData", self.localDeviceData["linkedEffektaData"], globalPublish = True, enableEcho = False)

    def getLinkedEffektaData(self):
        dataList = {}
        for device in self.configuration["managedEffektas"]:
            if device in self.localDeviceData:
                dataList.update({device:self.localDeviceData[device]})
        return EffektaController.getLinkedEffektaData(dataList)

    def manageLogicalLinkedEffektaData(self):
        """
        check logical linked Effekta data
        reset SocMonitor to 100% if floatMode is activ, and remember it
        send the data on topic ...out/linkedEffektaData if a new value arrived
        """
        # Daten erzeugen und wenn diese von den lokalen abweichen dann senden wir sie
        tempData = self.getLinkedEffektaData()
        if self.localDeviceData["linkedEffektaData"] != tempData:
            self.localDeviceData["linkedEffektaData"] = tempData
            self.sendLinkedEffektaData()

        if self.localDeviceData["linkedEffektaData"]["FloatingModeOr"]:
            if not self.ResetSocSent:
                self.resetSocMonitor()
                # Wir setzen hier einen eventuellen Skript error zurück. Wenn der Inverter in Floatmode schaltet dann ist der Akku voll und der SOC Monitor auf 100% gesetzt
                self.setSkriptValues("Error", False)
            self.ResetSocSent = True
        else:
            self.ResetSocSent = False

    def modifyRelaisData(self, relayStates = None, expectedStates = None) -> bool:
        '''
        Sets relay output values and publishes new states
        If check values have been given the relay states will be checked before they will be changed, it's not necessary to give all existing relays but only given ones will be checked, the others will be ignored

        @param relayStates          new values the relays should be switched to
        @param expectedStates       values the relays should already be set to before any given relayStates are set
                                    values will be set to expected state if current state is different

        @result                     True in case all given checks are successful (what is the case if none has been given), False if at least one real state differs from expected state
        '''
        checkResult = True          # used as return value, will be set to False if any "expect compare" fails
        contentChanged = False      # if set to True an update message will be published

        # try to search any relay not in expected state
        if expectedStates is not None:
            for relay in expectedStates:
                if self.localRelaisData[BasicUsbRelais.gpioCmd][relay] != expectedStates[relay]:
                    checkResult = False
                    self.logger.error(self, f"Relay {relay} is in state {self.localRelaisData[BasicUsbRelais.gpioCmd][relay]} but expected state is {expectedStates[relay]}")
                    self.localRelaisData[BasicUsbRelais.gpioCmd][relay] = expectedStates[relay]
                    contentChanged = True

        # if relay states have been given update current values and ensure a message is published (even if old and new values are identically)
        if relayStates is not None:
            self.localRelaisData[BasicUsbRelais.gpioCmd].update(relayStates)
            contentChanged = True

        # if any value has been changed publish an update message 
        if contentChanged:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.localRelaisData, globalPublish = False, enableEcho = False)

        return checkResult

    def initTransferRelais(self):
        # subscribe global to in topic to get PowerSaveMode
        self.aufNetzSchaltenErlaubt = True
        self.aufPvSchaltenErlaubt = True
        self.transferToNetzState = 0
        self.transferToPvState = 0
        self.errorTimerFinished = False
        self.localRelaisData = {
            BasicUsbRelais.gpioCmd : {
                self.REL_NETZ_AUS : "unknown",      # initially set all relay states to "unknown"
                self.REL_PV_AUS   : "unknown",
                self.REL_WR_1     : "unknown"
            }
        }
        self.modifyRelaisData(
            {
                self.REL_NETZ_AUS : self.AUS,   # initially all relays are OFF: - grid is enabled
                self.REL_PV_AUS   : self.AUS,   #                               - inverters are enabled
                self.REL_WR_1     : self.AUS    #                               - inverter output voltages are disabled
            },
            expectedStates = {}                 # no expected states during initialization
        )
        # @todo evtl überlegen ob es hier nicht sinnvoll ist, schalteRelaisAufNetz() aufzurufen. Dann schaltet die Anlage definiert um.
        self.currentMode = self.NETZ_MODE
        self.setSkriptValues("NetzRelais", self.currentMode)

    def manageUtilityRelais(self):
        '''
        startup               || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        ----------------------++--------------+------------+----------++------------------------------------
                              || OFF          | OFF        | OFF      || inverters are off, grid is active because hardware reasons but will be swich over to inverter mode whenever grid voltage is lost

        schalteRelaisAufPv    || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        ----------------------++--------------+------------+----------++------------------------------------
        initially             || OFF          | OFF        | OFF      || = Netz mode
        STATE_0               || OFF          | ON  <<<    | ON  <<<  || disable inverters, enable inverters output voltages, this prevents the system from switching over to inverter mode
        STATE_2               || OFF          | OFF <<<    | ON       || as soon as inverter output voltages are stable switch utility relay over to inverter mode

        schalteRelaisAufPv    || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        error case            ||              |            |          ||
        ----------------------++--------------+------------+----------++------------------------------------
        initially             || OFF          | OFF        | OFF      || = Netz mode
        STATE_0               || OFF          | ON  <<<    | ON  <<<  || disable inverters, enable inverters output voltages, this prevents the system from switching over to inverter mode
        STATE_1               || OFF          | ON         | OFF <<<  || disable inverter output voltages again since at least one inverter output voltage hasn't ever seen
        STATE_3               || OFF          | OFF <<<    | OFF      || back in "startup" state because of output voltage error

        schalteRelaisAufNetz  || REL_NETZ_AUS | REL_PV_AUS | REL_WR_1 ||
        ----------------------++--------------+------------+----------++------------------------------------
        initially             || OFF          | OFF        | ON       || = PV mode
        STATE_0               || OFF          | ON  <<<    | ON       || disable inverters what leads to automatic back switch to grid mode of the utility relay
        STATE_1               || OFF          | ON         | OFF <<<  || switch inverter output voltages off now
        STATE_2               || OFF          | OFF <<<    | OFF      || back in "startup" state
        '''
# REVIEW END
        # @TODO sollte erledigt sein mit dem SChaltplan vom Mane -> @todo schalte alle wr ein die bei Netzausfall automatisch gestartet wurden (nicht alle!). (ohne zwischenschritt relPvAus=ein), Bei Netzrückkehr wird dann automatisch die Funktion schalteRelaisAufNetz() aufgerufen.
        # Diese sollte aber bevor sie auf Netz schaltet in diesem Fall ca 1 min warten damit sich die Inverter synchronisieren können.
        def schalteRelaisAufNetz():
            # prüfen ob alle WR vom Netz versorgt werden
            # todo was ist wenn das Netz ausfällt während des umschaltens (sichereung)
            stateMode = self.TRANSFER_TO_NETZ

            tmpglobalEffektaData = self.getLinkedEffektaData()
            # first of all ensure that all inverters see their input voltages, otherwise a switch to the grid doesn't make any sense
            if not tmpglobalEffektaData["InputVoltageAnd"]:
                if self.timer(name = "timerToNetz", timeout = 600, firstTimeTrue = True):
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Keine Netzversorgung vorhanden!")
            elif self.transferToNetzState == self.switchToGrid.STATE_0:
                # if "InputVoltageAnd" was True but became False the timer still exists, so check it and remove it if necessary
                if self.timerExists("timerToNetz"):
                    self.timer(name = "timerToNetz", remove = True)
                self.transferToNetzState = self.switchToGrid.STATE_1
                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf Netz.")
                self.modifyRelaisData(
                    {
                        self.REL_PV_AUS   : self.EIN,       # inverters get disabled now
                    },
                    expectedStates = {
                        self.REL_NETZ_AUS : self.AUS,
                        self.REL_PV_AUS   : self.AUS,
                        self.REL_WR_1     : self.EIN,
                    }
                )
            elif self.transferToNetzState == self.switchToGrid.STATE_1:
                # warten bis Parameter geschrieben sind, wir wollen den Inverter nicht währendessen abschalten
                # @todo Wendeschütz lesen und timer erst starten, wenn laut Wendeschütz Umschaltung durchgeführt wurde

                # wait additional 30 seconds just to be sure grid voltages are stable
                if self.timer(name = "timerToNetz", timeout = 30, removeOnTimeout = True):
                    self.transferToNetzState = self.switchToGrid.STATE_2
                    self.modifyRelaisData(
                        {
                            self.REL_WR_1     : self.AUS,       # now switch inverter output voltages off
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.EIN,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
            elif self.transferToNetzState == self.switchToGrid.STATE_2:
                # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                #if self.timer(name = "timerToNetz", timeout = 35):
                if self.timer(name = "timerToNetz", timeout = 500, removeOnTimeout = True):
                    tmpglobalEffektaData = self.getLinkedEffektaData()
                    if tmpglobalEffektaData["OutputVoltageHighOr"]:
                        # Durch das ruecksetzten von PowersaveMode schalten wir als nächstes wieder zurück auf PV.
                        # Wir wollen im Fehlerfall keinen inkonsistenten Schaltzustand der Anlage darum schalten wir die Umrichter nicht aus.
                        self.setSkriptValues("PowerSaveMode", False)
                        self.aufNetzSchaltenErlaubt = False
                        # @todo nachdenken was hier sinnvoll ist. Momentan wird wieder zurück auf inverter geschaltet wenn kein Fehler am Inverter anliegt
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Wechselrichter konnte nicht abgeschaltet werden. Er hat nach Wartezeit immer noch Spannung am Ausgang! Die Automatische Netzumschaltung wurde deaktiviert.")
                        # Wir setzen den Status bereits hier ohne Rücklesen damit das relPvAus nicht zurückgesetzt wird. (siehe zurücklesen der Relais Werte)
                    else:
                        self.modifyRelaisData(
                            {
                                self.REL_PV_AUS   : self.AUS,       # inverters get enabled again
                            },
                            expectedStates = {
                                self.REL_NETZ_AUS : self.AUS,
                                self.REL_PV_AUS   : self.EIN,
                                self.REL_WR_1     : self.AUS,
                            }
                        )
                        # kurz warten damit das zurücklesen nicht zu schnell geht
                        time.sleep(0.5)     # @todo gruselig, sollte durch Timer ersetzt werden!!!
                    self.transferToNetzState = self.switchToGrid.STATE_0
                    # Wir wollen nicht zu oft am Tag umschalten. Maximal 1 mal am Tag auf Netz.
                    self.aufNetzSchaltenErlaubt = False
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf Netz.")
                    stateMode = self.NETZ_MODE
            return stateMode

        def schalteRelaisAufPv():
            stateMode = self.TRANSFER_TO_INVERTER

            if self.transferToPvState == self.switchToInverter.STATE_0:
                # ensure that no inverter sees any output voltage, otherwise there is sth. wrong
                if tmpglobalEffektaData["OutputVoltageHighOr"]:
                    self.modifyRelaisData(
                        {
                            # all these states are already expected but sth. is wrong and inverter output voltages are on, so try to switch off again
                            self.REL_WR_1     : self.AUS,       # this should lead to a switch over to grid mode
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.AUS,
                            self.REL_WR_1     : self.AUS,
                        }
                    )
                    if self.timer(name = "timerToPv", timeout = 600, firstTimeTrue = True):
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Output liefert bereits Spannung!")
                    # @todo auch hier kommen wir ggf. nie wieder raus, dann doch besser gezielt beenden!
                # warten bis Parameter geschrieben sind
                elif self.timer(name = "timerToPv", timeout = 30, removeOnTimeout = True):
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf Inverter.")
                    # grid mode has to be active, inverter mode has to be inactive, switch on inverter output voltages
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.EIN,       # disable inverters, stay in grid mode
                            self.REL_WR_1     : self.EIN,       # enable inverter output voltages
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.AUS,
                            self.REL_WR_1     : self.AUS,
                        }
                    )
                    self.transferToPvState = self.switchToInverter.STATE_1
            elif self.transferToPvState == self.switchToInverter.STATE_1:
                if self.timer(name = "timeoutAcOut", timeout = 100, removeOnTimeout = True):                                # wait until inverter output voltages are ON and stable
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Wartezeit zu lange. Keine Ausgangsspannung am WR erkannt.")
                    # Wir schalten die Funktion aus
                    self.setSkriptValues("PowerSaveMode", False)
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Die Automatische Netzumschaltung wurde deaktiviert.")
                    self.modifyRelaisData(
                        {
                            self.REL_WR_1     : self.AUS,       # disable inverter output voltages again since there wasn't detected any output voltages in time
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.EIN,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
                    # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                    self.sleeptime = 600    # set long sleep time for following state
                    self.transferToPvState = self.switchToInverter.STATE_3
                    stateMode = self.OUTPUT_VOLTAGE_ERROR
                elif self.getLinkedEffektaData()["OutputVoltageHighAnd"] == True:
                    self.timer(name = "timeoutAcOut", remove = True)    # timer hasn't timed out yet, so removeOnTimeout didn't get active, therefore, the timer has to be removed manually
                    self.transferToPvState = self.switchToInverter.STATE_2
                    self.sleeptime = 10     # set short sleep time for following state
            elif self.transferToPvState == self.switchToInverter.STATE_2:
                if self.timer(name = "waitForOut", timeout = self.sleeptime, removeOnTimeout = True):
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.AUS,       # enable inverters what makes utility relay switch over to inverter mode since inverter output voltages are up
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.EIN,
                            self.REL_WR_1     : self.EIN,
                        }
                    )
                    self.transferToPvState = self.switchToInverter.STATE_0
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf Inverter.")
                    stateMode = self.PV_MODE
            elif self.transferToPvState == self.switchToInverter.STATE_3:
                # @todo wir sind hier noch nicht fertig, die Zeile oben "stateMode = self.OUTPUT_VOLTAGE_ERROR" führt noch dazu, dass wir hier nie wieder herkommen und wenn wir das fixen dann haben wir das Problem, dass wir sofort wieder versuchen umzuschalten...
                if self.timer(name = "waitForOut", timeout = self.sleeptime, removeOnTimeout = True):
                    self.modifyRelaisData(
                        {
                            self.REL_PV_AUS   : self.AUS,       # enable inverters what makes utility relay stay in grid mode since inverter output voltages are down
                        },
                        expectedStates = {
                            self.REL_NETZ_AUS : self.AUS,
                            self.REL_PV_AUS   : self.EIN,
                            self.REL_WR_1     : self.AUS,
                        }
                    )
                    self.transferToPvState = self.switchToInverter.STATE_0
                    self.publishAndLog(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung ist fehlgeschlagen und steht jetzt wieder auf Netz aber im Fehlermode was ein erneutes Umschalten auf PV verhindert.")
                    stateMode = self.NETZ_MODE
            return stateMode

# @todo Netzausfallerkennung ist noch nicht vorhanden, aktuell schaltet die externe Schaltung in dem Fall das Wendeschütz um und wir hängen auf den Wechselrichtern, wir sollten das erkennen und REL_NETZ_AUS aktivieren bis wir erkennen, daß das Netz wieder da ist und dann gezielt zurück schalten oder sowas in der Art!!!


        def switchToUtiliyAllowed():
            return self.aufNetzSchaltenErlaubt and (self.currentMode in [self.PV_MODE, self.TRANSFER_TO_NETZ])

        def switchToInverterAllowed():
            return self.aufPvSchaltenErlaubt and (self.currentMode in [self.NETZ_MODE, self.TRANSFER_TO_INVERTER])

        def switchToDesiredMode(mode):
            if mode == self.AKKU_MODE:
                mode = self.PV_MODE
            # VerbraucherAkku -> schalten auf PV, VerbraucherNetz -> schalten auf Netz, VerbraucherPVundNetz -> zwischen 6-22 Uhr auf PV sonst Netz
            # Wenn der transfer noch nicht beendet wurde dann rufen wir die Funktionen so lange auf bis das der Fall ist
            if (mode == self.PV_MODE and switchToInverterAllowed()) or (mode == self.NETZ_MODE and self.currentMode == self.TRANSFER_TO_INVERTER):
                self.currentMode = schalteRelaisAufPv()
                if self.currentMode == self.OUTPUT_VOLTAGE_ERROR:
                    #@todo switch back to grid!!!
                    pass
            elif (mode == self.NETZ_MODE and switchToUtiliyAllowed()) or (mode == self.PV_MODE and self.currentMode == self.TRANSFER_TO_NETZ):
                self.currentMode = schalteRelaisAufNetz()

        # todo hier input abfragen der ein Rückfallen bei stromausfall und Netzbetrieb liest (inverter schütz)

        now = datetime.datetime.now()

        tmpglobalEffektaData = self.getLinkedEffektaData()
        if tmpglobalEffektaData["ErrorPresentOr"] == False:
            # only if timer exists errorTimerFinished can be True
            if self.timerExists("ErrorTimer"):
                self.timer(name = "ErrorTimer", remove = True)
                self.errorTimerFinished = False

            if self.scriptValues["PowerSaveMode"] == True:
                # Wir resetten die Variable einmal am Tag
                # Nach der Winterzeit um 21 Uhr
                # @todo mit localtime könnte man auch die korrekte Uhrzeit bekommen
                if now.hour == 20 and now.minute == 1:
                    self.aufNetzSchaltenErlaubt = True
                    self.aufPvSchaltenErlaubt = True
                switchToDesiredMode(self.scriptValues["WrMode"])
            else: # Powersave off
                # Wir resetten die Verriegelung hier auch, damit man durch aus und einchalten von PowerSaveMode das Umschalten auf Netz wieder frei gibt.
                self.aufNetzSchaltenErlaubt = True
                switchToDesiredMode(self.PV_MODE)
                if self.currentMode == self.OUTPUT_VOLTAGE_ERROR:
                    self.aufPvSchaltenErlaubt = False
        else: # Fehler vom Inverter
            # wir erlauben das umschalten auf netz damit die anlage auch ummschalten kann
            self.aufNetzSchaltenErlaubt = True

            # Wenn ein Fehler 80s ansteht, dann werden wir aktiv und schalten auf Netz um
            if self.errorTimerFinished:
                switchToDesiredMode(self.NETZ_MODE)
            elif self.timer(name = "ErrorTimer", timeout = 80):
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Fehler am Inverter erkannt. Wir schalten auf Netz.")
                    # todo: wenn der fehler wieder weg ist nach dem umschalten auf Netz und abschlten der inverter, dann fallen wir in den if zweig und die Netzumschaltung schaltet wieder. Es könnte ein toggeln entstehen.
                    self.errorTimerFinished = True

        # Status des Netzrelais in scriptValues übertragen damit er auch gesendet wird
        self.setSkriptValues("NetzRelais", self.currentMode)


    def wetterPrognoseSchlecht(self, day : str) -> bool:
        result = False
        if day in self.localDeviceData[self.configuration["weatherName"]]:
            if self.localDeviceData[self.configuration["weatherName"]][day] != None:
                if self.localDeviceData[self.configuration["weatherName"]][day]["Sonnenstunden"] <= self.scriptValues["wetterSchaltschwelleNetz"]:
                    result = True
            else:
                # todo macht hier keinen Sinn, error zyklisch mit timer schicken wenn dict leer ist
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")
        return result


    def wetterPrognoseMorgenSchlecht(self):
        # Wir wollen abschätzen ob wir auf Netz schalten müssen dazu soll abends geprüft werden ob noch genug energie für die Nacht zur verfügung steht
        # Dazu wird geprüft wie das Wetter (Sonnenstunden) am nächsten Tag ist und dementsprechend früher oder später umgeschaltet.
        # Wenn das Wetter am nächsten Tag schlecht ist macht es keinen Sinn den Akku leer zu machen und dann im Falle einer Unterspannung vom Netz laden zu müssen.
        # Die Prüfung ist nur Abends aktiv da man unter Tags eine andere Logik haben möchte.
        # In der Sommerzeit löst now.hour = 17 um 18 Uhr aus, In der Winterzeit dann um 17 Uhr
        return self.wetterPrognoseSchlecht("Tag_1")

    def wetterPrognoseHeuteSchlecht(self):
        return self.wetterPrognoseSchlecht("Tag_0")


    def minAkkustandNacht(self):
        return self.scriptValues["verbrauchNachtAkku"] + self.scriptValues["MinSoc"]

    def akkuStandAusreichend(self):
        return self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.minAkkustandNacht()

    def initInverter(self):
        if self.configuration["initModeEffekta"] == self.AUTO_MODE:
            if self.localDeviceData["AutoInitRequired"]:
                self.autoInitInverter()
        elif self.configuration["initModeEffekta"] == self.AKKU_MODE:
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.setSkriptValues("AutoMode", False)
        elif self.configuration["initModeEffekta"] == self.NETZ_MODE:
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.setSkriptValues("AutoMode", False)
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

        if message["topic"].find("UsbRelaisWd") != -1:
            Supporter.debugPrint(f"{self.name} got message {message}", color = "GREEN")
            #{'topic': 'AccuControl/UsbRelaisWd1/out', 'global': False, 'content': {'inputs': {'Input3': '0', 'readbackGrid': '0', 'readbackInverter': '0', 'readbackSolarContactor': '0'}}}
            #{'topic': 'AccuControl/UsbRelaisWd2/out', 'global': False, 'content': {'inputs': {'Input0': '0', 'Input1': '0', 'Input2': '0', 'Input3': '0'}}}
            #"gridActive"
            #"inverterActive"

        # check if its our own topic
        if self.createOutTopic(self.getObjectTopic()) in message["topic"]:
            # we use it and unsubscribe
            self.updateScriptValues(message["content"])
            self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))

            # timer didn't time out but we received a message from MQTT broker so remove the surely still existing timer
            if self.timerExists("timeoutMqtt"):
                self.timer(name = "timeoutMqtt", remove = True)

            self.localDeviceData["initialMqttTimeout"] = True

            # we got our own Data so we dont need a auto init inverters
            self.localDeviceData["AutoInitRequired"] = False
        else:
            # check if the incoming value is part of self.setableScriptValues and if true then take the new value
            for key in self.setableScriptValues:
                if key in message["content"]:
                    if type(self.scriptValues[key]) == float and type(message["content"][key]) == int:
                        message["content"][key] = float(message["content"][key])
                    if type(self.scriptValues[key]) == int and type(message["content"][key]) == float:
                        message["content"][key] = int(message["content"][key])
                    try:
                        if type(message["content"][key]) == type(self.scriptValues[key]):
                            self.setSkriptValues(key, message["content"][key])
                        else:
                            self.logger.error(self, "Wrong datatype globally received.")
                    except Exception as ex:
                        self.logger.error(self, f"Wrong datatype globally received, exception: {ex}")

            if message["content"] in self.manualCommands:
                # if it is a dummy command. we do nothing
                if message["content"] != self.dummyCommand:
                    self.setSkriptValues("AutoMode", False)
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

            # check if a expected device sent a msg and store it
            for key in self.expectedDevices:
                if key in message["topic"]:
                    if key in self.localDeviceData: # Filter first run
                        # check FullChargeRequired from BMS for rising edge
                        if key == self.configuration["bmsName"] and self.checkForKeyAndCheckRisingEdge(self.localDeviceData[self.configuration["bmsName"]], message["content"], "FullChargeRequired"):
                            self.setSkriptValues("FullChargeRequired", True)
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
        self.publishAndLog(Logger.LOG_LEVEL.INFO, "---", logMessage = False)      # set initial value, don't log it!
        self.publishAndLog(Logger.LOG_LEVEL.ERROR, "---", logMessage = False)     # set initial value, don't log it!

        self.tagsIncluded(["managedEffektas", "initModeEffekta", "socMonitorName", "bmsName"])
        self.tagsIncluded(["weatherName"], optional = True, default = "noWeatherConfigured")
        self.tagsIncluded(["inputs"], optional = True, default = [])

        # if there was only one module given for inputs convert it to a list
        if type(self.configuration["inputs"]) != list:
            self.configuration["inputs"] = [self.configuration["inputs"]]

        # Threadnames we have to wait for a initial message. The worker need this data.
        self.expectedDevices = []
        self.expectedDevices.append(self.configuration["socMonitorName"])
        self.expectedDevices.append(self.configuration["bmsName"])
        # add managedEffekta List, funktion getLinkedEffektaData nedds this data
        self.expectedDevices += self.configuration["managedEffektas"]

        self.optionalDevices = []
        self.optionalDevices.append(self.configuration["weatherName"])
        self.optionalDevices += self.configuration["inputs"]

        # init some variables
        self.localDeviceData = {"expectedDevicesPresent": False, "initialMqttTimeout": False, "initialRelaisTimeout": False, "AutoInitRequired": True, "linkedEffektaData":{}, self.configuration["weatherName"]:{}}
        # init lists of direct setable values, sensors or commands
        self.setableSlider = {"schaltschwelleAkkuTollesWetter":20.0, "schaltschwelleAkkuRussia":100.0, "schaltschwelleNetzRussia":80.0, "NetzSchnellladenRussia":65.0, "schaltschwelleAkkuSchlechtesWetter":45.0, "schaltschwelleNetzSchlechtesWetter":30.0}
        self.niceNameSlider = {"schaltschwelleAkkuTollesWetter":"Akku gutes Wetter", "schaltschwelleAkkuRussia":"Akku USV", "schaltschwelleNetzRussia":"Netz USV", "NetzSchnellladenRussia":"Laden USV", "schaltschwelleAkkuSchlechtesWetter":"Akku schlechtes Wetter", "schaltschwelleNetzSchlechtesWetter":"Netz schlechtes Wetter"}
        self.setableSwitch = {"Akkuschutz":False, "RussiaMode": False, "PowerSaveMode" : False, "AutoMode": True, "FullChargeRequired": False}
        self.sensors = {"WrNetzladen":False,  "Error":False, "WrMode":"", "schaltschwelleAkku":100.0, "schaltschwelleNetz":20.0, "NetzRelais": ""}
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
        self.AKKU_MODE = "Akku"
        self.NETZ_MODE = "Netz"
        self.AUTO_MODE = "Auto"
        self.PV_MODE = "Inverter"
        self.OUTPUT_VOLTAGE_ERROR = "OutputVoltageError"
        self.TRANSFER_TO_INVERTER = "transferToInverter"
        self.TRANSFER_TO_NETZ     = "transferToNetz"
        self.REL_WR_1     = "relWr"
        self.REL_PV_AUS   = "relPvAus"
        self.REL_NETZ_AUS = "relNetzAus"
        self.EIN = "1"
        self.AUS = "0"

        # init TransferRelais to switch all Relais to initial position
        self.initTransferRelais()


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


    def threadMethod(self):
        self.sendeMqtt = False

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
            self.manageLogicalLinkedEffektaData()
            now = datetime.datetime.now()

            self.passeSchaltschwellenAn()

            # do some initialization if this code position is reached for the first time during startup
            if not self.startupInitialization:
                self.startupInitialization = True        # do startup initialization only once
                self.addLinkedEffektaDataToHomeautomation()
                self.initInverter()
                # init TransferRelais a second Time to overwrite scriptValues["NetzRelais"] with the initial value. The initial MQTT msg maybe wrote last state to this key!
                self.initTransferRelais()

            # Wir prüfen als erstes ob die Freigabe vom BMS da ist und kein Akkustand Error vorliegt
            if self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"] and not self.scriptValues["Error"]:
                # Wir wollen erst prüfen ob das skript automatisch schalten soll.
                if self.scriptValues["AutoMode"]:
                    # todo self.setSkriptValues("Akkuschutz", False) Über Wetter?? Was ist mit "Error: Ladestand weicht ab"
                    if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] > self.scriptValues["AkkuschutzAbschalten"]:
                        # above self.scriptValues["AkkuschutzAbschalten"] threshold then "Akkuschutz" is disabled
                        self.setSkriptValues("Akkuschutz", False)

                    # Wir prüfen ob wir wegen zu wenig prognostiziertem Ertrag den Akkuschutz einschalten müssen. Der Akkuschutz schaltet auf einen höheren (einstellbar) SOC Bereich um.
                    if not self.scriptValues["Akkuschutz"]:
                        if self.wetterPrognoseMorgenSchlecht() and (not self.akkuStandAusreichend()):
                            if (17 <= now.hour < 23) or ((12 <= now.hour < 23) and self.wetterPrognoseHeuteSchlecht()):
                                #self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                                self.setSkriptValues("Akkuschutz", True)
                                self.publishAndLog(Logger.LOG_LEVEL.INFO, "Sonnen Stunden < %ih -> schalte Akkuschutz ein." %self.scriptValues["wetterSchaltschwelleNetz"])

                    self.passeSchaltschwellenAn()

                    # behandeln vom Laden in RussiaMode (USV)
                    if self.scriptValues["RussiaMode"]:
                        self.NetzLadenAusGesperrt = True
                        if self.scriptValues["WrNetzladen"] == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= (self.scriptValues["schaltschwelleNetz"] - self.scriptValues["verbrauchNachtNetz"]):
                            self.schalteAlleWrNetzSchnellLadenEin(self.configuration["managedEffektas"])
                        if self.scriptValues["WrNetzladen"] == True and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleNetz"]:
                            self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])

                    if self.scriptValues["WrMode"] == self.AKKU_MODE:
                        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= self.scriptValues["schaltschwelleNetz"]:
                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.publishAndLog(Logger.LOG_LEVEL.INFO, "%iP erreicht -> schalte auf Netz." %self.scriptValues["schaltschwelleNetz"])
                    elif self.scriptValues["WrMode"] == self.NETZ_MODE:
                        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleAkku"]:
                            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
                            self.NetzLadenAusGesperrt = False
                            self.publishAndLog(Logger.LOG_LEVEL.INFO, "%iP erreicht -> Schalte auf Akku"  %self.scriptValues["schaltschwelleAkku"])
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
                    self.setSkriptValues("Akkuschutz", True)
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, f'Ladestand fehlerhaft')
                # wir setzen einen error weil das nicht plausibel ist und wir hin und her schalten sollte die freigabe wieder kommen
                # wir wollen den Akku erst bis 100 P aufladen
                if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.scriptValues["schaltschwelleAkkuTollesWetter"]:
                    self.setSkriptValues("Error", True)
                    # Wir setzen den Error zurück wenn der Inverter auf Floatmode umschaltet. Wenn diese bereits gesetzt ist dann müssen wir das Skript beenden da der Error sonst gleich wieder zurück gesetzt werden würde
                    if self.localDeviceData["linkedEffektaData"]["FloatingModeOr"] == True:
                        raise Exception(f'SOC: {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}, EntladeFreigabe: {self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"]}, und FloatMode von Inverter aktiv! Unplausibel!') 
                    self.publishAndLog(Logger.LOG_LEVEL.ERROR, 'Error wurde gesetzt, reset bei vollem Akku. FloatMode.')
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, f'Unterspannung BMS bei {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}%')

            self.passeSchaltschwellenAn()

            # for the first 30 seconds after PowerPlant has been started the relay will not be switched, that suppresses unnecessary relay switching processes when PowerPlant is started several times, e.g. because of debugging reasons
            if self.localDeviceData["initialRelaisTimeout"] or self.timer(name = "timeoutTransferRelais", timeout = 30, removeOnTimeout = True):
                self.manageUtilityRelais()
                self.localDeviceData["initialRelaisTimeout"] = True             # from now on this value will ensure that the previous "if" becomes True, since timer has already removed itself

            # Do mqtt values have to be updated?
            if self.sendeMqtt:
                self.sendeMqtt = False
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.scriptValues, globalPublish = True, enableEcho = False)
        else:
            if self.timer(name = "timeoutExpectedDevices", timeout = 10*60):
                self.publishAndLog(Logger.LOG_LEVEL.ERROR, "Es haben sich nicht alle erwarteten Devices gemeldet!")

                for device in self.expectedDevices:
                    if not device in self.localDeviceData:
                        self.publishAndLog(Logger.LOG_LEVEL.ERROR, f"Device: {device} fehlt!")
                raise Exception("Some devices are missing after timeout!")


    def threadBreak(self):
        time.sleep(0.1)

