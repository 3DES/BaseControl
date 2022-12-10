import time
import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from GridLoad.SocMeter import SocMeter
from Base.Supporter import Supporter
from Inverter.EffektaController import EffektaController
import Base
import subprocess
import json


class PowerPlant(Worker):
    '''

    Used values, devices and classmethods:
    All required devices are blocking a startup until data arrives!
    required:
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
            
            BMS:
                    BmsEntladeFreigabe                                          bool, key in BMS data dict
                    BmsMsgCounter                                               todo, implement! int, counter for required BMS msg to provide stuckAt errors. A new number triggers watchdog
                    
            SocMonitor:
                    Prozent                                                     float, key in Soc data dict
    optional:
            Wetter:
                    Tag_0                                                       dict, key in wetter data dict
                        Sonnenstunden                                           int, key in Tag_0 dict
                    Tag_1                                                       dict, key in wetter data dict
                        Sonnenstunden                                           int, key in Tag_1 dict

    Data output from powerPlant:
            Inverter:
                    Commands to each given inverter. (managedEffektas)
            SocMonitor:
                    sends "resetSoc" if floatMode from inverter is set (rising edge)


    '''


    def passeSchaltschwellenAn(self):
        #SOC Schaltschwellen in Prozent
        self.SkriptWerte["schaltschwelleNetzLadenaus"] = 12.0
        self.SkriptWerte["schaltschwelleNetzLadenein"] = 6.0
        self.SkriptWerte["MinSoc"] = 10.0
        self.SkriptWerte["SchaltschwelleAkkuTollesWetter"] = 20.0
        self.SkriptWerte["AkkuschutzAbschalten"] = self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"] + 15.0
        # todo Automatisch ermitteln
        self.SkriptWerte["verbrauchNachtAkku"] = 25.0
        self.SkriptWerte["verbrauchNachtNetz"] = 3.0

        # Russia Mode hat Vorrang ansonsten entscheiden wir je nach Wetter (Akkuschutz)
        if self.SkriptWerte["RussiaMode"]:
            # Wir wollen die Schaltschwellen nur übernehmen wenn diese plausibel sind
            if self.SkriptWerte["schaltschwelleNetzRussia"] < self.SkriptWerte["schaltschwelleAkkuRussia"]:
                if self.SkriptWerte["schaltschwelleAkku"] != self.SkriptWerte["schaltschwelleAkkuRussia"]:
                    self.sendeMqtt = True
                self.SkriptWerte["schaltschwelleAkku"] = self.SkriptWerte["schaltschwelleAkkuRussia"]
                self.SkriptWerte["schaltschwelleNetz"] = self.SkriptWerte["schaltschwelleNetzRussia"]
        else:
            if self.SkriptWerte["Akkuschutz"]:
                # Wir wollen die Schaltschwellen nur übernehmen wenn diese plausibel sind
                if self.SkriptWerte["schaltschwelleNetzSchlechtesWetter"] < self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"]:
                    if self.SkriptWerte["schaltschwelleAkku"] != self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"]:
                        self.sendeMqtt = True
                    self.SkriptWerte["schaltschwelleAkku"] = self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"]
                    self.SkriptWerte["schaltschwelleNetz"] = self.SkriptWerte["schaltschwelleNetzSchlechtesWetter"]
            else:
                # Wir wollen die Schaltschwellen nur übernehmen wenn diese plausibel sind
                if self.SkriptWerte["MinSoc"] < self.SkriptWerte["schaltschwelleAkkuTollesWetter"]:
                    if self.SkriptWerte["schaltschwelleAkku"] != self.SkriptWerte["schaltschwelleAkkuTollesWetter"]:
                        self.sendeMqtt = True
                    self.SkriptWerte["schaltschwelleAkku"] = self.SkriptWerte["schaltschwelleAkkuTollesWetter"]
                    self.SkriptWerte["schaltschwelleNetz"] = self.SkriptWerte["MinSoc"]

        if self.SkriptWerte["schaltschwelleNetz"] < self.SkriptWerte["MinSoc"]:
            self.SkriptWerte["schaltschwelleNetz"] = self.SkriptWerte["MinSoc"]

        # Wetter Sonnenstunden Schaltschwellen
        self.SkriptWerte["wetterSchaltschwelleNetz"] = 6    # Einheit Sonnnenstunden

    def sendEffektaData(self, data, effektas):
        for inverter in effektas:
            self.mqttPublish(self.createInTopic(self.get_projectName() + "/" + inverter), data, globalPublish = False, enableEcho = False)

    def schalteAlleWrAufAkku(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToBattery(), effektas)
        self.SkriptWerte["WrMode"] = self.Akkumode
        self.SkriptWerte["WrNetzladen"] = False
        self.sendeMqtt = True

    def schalteAlleWrAufNetzOhneNetzLaden(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtility(), effektas)
        self.SkriptWerte["WrMode"] = self.NetzMode
        self.SkriptWerte["WrNetzladen"] = False
        self.sendeMqtt = True

    def schalteAlleWrNetzLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOn(), effektas)
        self.SkriptWerte["WrMode"] = self.NetzMode
        self.SkriptWerte["WrNetzladen"] = True
        self.sendeMqtt = True

    def schalteAlleWrNetzLadenAus(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityChargeOff(), effektas)
        self.SkriptWerte["WrNetzladen"] = False
        self.sendeMqtt = True

    def schalteAlleWrAufNetzMitNetzladen(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchToUtilityWithUvDetection(), effektas)
        self.SkriptWerte["WrMode"] = self.NetzMode
        self.SkriptWerte["WrNetzladen"] = True
        self.sendeMqtt = True

    def schalteAlleWrNetzSchnellLadenEin(self, effektas):
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityFastChargeOn(), effektas)
        self.SkriptWerte["WrMode"] = self.NetzMode
        self.SkriptWerte["WrNetzladen"] = True
        self.sendeMqtt = True

    def resetSocMonitor(self):
        self.mqttPublish(self.createInTopic(self.createProjectTopic(self.configuration["socMonitorName"])), "resetSoc", globalPublish = False, enableEcho = False)

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
        tempData = self.getLinkedEffektaData()
        if tempData != self.localDeviceData["linkedEffektaData"]:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + "linkedEffektaData", tempData, globalPublish = True, enableEcho = False)
        self.localDeviceData["linkedEffektaData"] = tempData
        if self.localDeviceData["linkedEffektaData"]["FloatingModeOr"] == True:
            if not self.ResetSocSended:
                self.resetSocMonitor()
                # Wir setzen hier einen eventuellen Skript error zurück. Wenn der Inverter in Floatmode schaltet dann ist der Akku voll und der SOC Monitor auf 100% gesetzt
                self.SkriptWerte["Error"] = False
            self.ResetSocSended = True
        else:
            self.ResetSocSended = False

    def getGpioTopic(self):
        return self.createInTopic(self.createProjectTopic(self.configuration["relaisNames"]["deviceName"]))

    def initTransferRelais(self):
        # subscribe global to in topic to get PowerSaveMode
        self.aufNetzSchaltenErlaubt = True
        self.aufPvSchaltenErlaubt = True
        self.transferToNetzState = 0
        self.TransferToPvState = 0
        #self.netzMode = "Netz"
        self.pvMode = "Inverter"
        self.transferToInverter = "transferToInverter"
        self.transferToNetz = "transferToNetz"
        self.OutputVoltageError = "OutputVoltageError"
        self.aktualMode = self.NetzMode    # wir gehen davon aus, dass die Relais nach dem Starten aus sind, das entspricht NetzMode
        self.relWr1 = self.configuration["relaisNames"]["relWr1"]
        self.relWr2 = self.configuration["relaisNames"]["relWr2"]
        self.relPvAus = self.configuration["relaisNames"]["relPvAus"]
        self.relNetzAus = self.configuration["relaisNames"]["relNetzAus"]
        self.ein = "1"
        self.aus = "0"
        self.localRelaisData = {self.configuration["relaisNames"]["deviceName"]:{self.relNetzAus: "unknown", self.relPvAus: "unknown", self.relWr2: "unknown", self.relWr1: "unknown"}}

    def manageTransferRelais(self):
        def modifyRelaisData(relais, value, sendValue = False):
            self.localRelaisData[self.configuration["relaisNames"]["deviceName"]].update({relais:value})
            if sendValue:
                self.mqttPublish(self.getGpioTopic(), self.localRelaisData, globalPublish = False, enableEcho = False)

        def schalteRelaisAufNetz():
            match self.transferToNetzState:
                case 0:
                    self.transferToNetzState+=1
                    self.myPrint(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf Netz.")
                    modifyRelaisData(self.relNetzAus, self.aus)
                    modifyRelaisData(self.relPvAus, self.ein, True)
                case 1:
                    # warten bis Parameter geschrieben sind, wir wollen den Inverter nicht währendessen abschalten
                    if self.timer(name = "timerToNetz", timeout = 30):
                        self.timer(name = "timerToNetz", remove = True)
                        self.transferToNetzState+=1
                        modifyRelaisData(self.relWr1, self.aus)
                        modifyRelaisData(self.relWr2, self.aus, True)
                case 2:
                    # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                    #if self.timer(name = "timerToNetz", timeout = 35):
                    if self.timer(name = "timerToNetz", timeout = 500):
                        self.timer(name = "timerToNetz", remove = True)
                        tmpglobalEffektaData = self.getLinkedEffektaData()
                        if tmpglobalEffektaData["OutputVoltageHighOr"] == True:
                            # Durch das ruecksetzten von PowersaveMode schalten wir als nächstes wieder zurück auf PV. 
                            # Wir wollen im Fehlerfall keinen inkonsistenten Schaltzustand der Anlage darum schalten wir die Umrichter nicht aus.
                            self.SkriptWerte["PowerSaveMode"] = False
                            self.aufNetzSchaltenErlaubt = False
                            self.sendeMqtt = True
                            # @todo nachdenken was hier sinnvoll ist. Momentan wird wieder zurück auf inverter geschaltet
                            self.myPrint(Logger.LOG_LEVEL.ERROR, "Wechselrichter konnte nicht abgeschaltet werden. Er hat nach Wartezeit immer noch Spannung am Ausgang! Die Automatische Netzumschaltung wurde deaktiviert.")
                            # Wir setzen den Status bereits hier ohne Rücklesen damit das relPvAus nicht zurückgesetzt wird. (siehe zurücklesen der Relais Werte)
                        else:
                            modifyRelaisData(self.relPvAus, self.aus, True)
                            # kurz warten damit das zurücklesen nicht zu schnell geht
                            time.sleep(0.5)
                        self.transferToNetzState = 0
                        # Wir wollen nicht zu oft am Tag umschalten. Maximal 1 mal am Tag auf Netz.
                        self.aufNetzSchaltenErlaubt = False
                        self.myPrint(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf Inverter.")
                        return self.NetzMode
            return self.transferToNetz

        def schalteRelaisAufPv():
            if self.TransferToPvState == 0:
                # warten bis Parameter geschrieben sind
                if self.timer(name = "timerToPv", timeout = 30):
                    self.timer(name = "timerToPv", remove = True)
                    self.myPrint(Logger.LOG_LEVEL.INFO, "Schalte Netzumschaltung auf PV.")
                    modifyRelaisData(self.relNetzAus, self.aus)
                    modifyRelaisData(self.relPvAus, self.ein)
                    modifyRelaisData(self.relWr1, self.ein)
                    modifyRelaisData(self.relWr2, self.ein, True)
                    self.TransferToPvState+=1
            elif self.TransferToPvState == 1:
                if self.timer(name = "timeoutAcOut", timeout = 100):
                    self.timer(name = "timeoutAcOut", remove = True)
                    self.myPrint(Logger.LOG_LEVEL.ERROR, "Wartezeit zu lange. Keine Ausgangsspannung am WR erkannt.")
                    #Wir schalten die Funktion aus
                    self.SkriptWerte["PowerSaveMode"] = False
                    self.sendeMqtt = True
                    self.myPrint(Logger.LOG_LEVEL.ERROR, "Die Automatische Netzumschaltung wurde deaktiviert.")
                    modifyRelaisData(self.relWr1, self.aus)
                    modifyRelaisData(self.relWr2, self.aus, True)
                    # wartezeit setzen damit keine Spannung mehr am ausgang anliegt.Sonst zieht der Schütz wieder an und fällt gleich wieder ab. Netzspannung auslesen funktioniert hier nicht.
                    self.sleeptime = 600
                    self.TransferToPvState+=1
                    return self.OutputVoltageError
                elif self.getLinkedEffektaData()["OutputVoltageHighAnd"] == True:
                    self.timer(name = "timeoutAcOut", remove = True)
                    self.TransferToPvState+=1
                    self.sleeptime = 10
            elif self.TransferToPvState == 2:
                if self.timer(name = "waitForOut", timeout = self.sleeptime):
                    self.timer(name = "waitForOut", remove = True)
                    modifyRelaisData(self.relPvAus, self.aus, True)
                    self.TransferToPvState = 0
                    self.myPrint(Logger.LOG_LEVEL.INFO, "Die Netzumschaltung steht jetzt auf PV.")
                    return self.pvMode
            return self.transferToInverter

        def switchToUtiliyAllowed():
            return self.aufNetzSchaltenErlaubt == True and (self.aktualMode == self.pvMode or self.aktualMode == self.transferToNetz)

        def switchToInverterAllowed():
            return self.aufPvSchaltenErlaubt == True and (self.aktualMode == self.NetzMode or self.aktualMode == self.transferToInverter)

        now = datetime.datetime.now()

        tmpglobalEffektaData = self.getLinkedEffektaData()
        if tmpglobalEffektaData["ErrorPresentOr"] == False:
            if self.SkriptWerte["PowerSaveMode"] == True:
                # Wir resetten die Variable einmal am Tag
                # Nach der Winterzeit um 21 Uhr
                if now.hour == 21 and now.minute == 1:
                    self.aufNetzSchaltenErlaubt = True
                    self.aufPvSchaltenErlaubt = True
                    self.OutputVoltageError = False
                # VerbraucherAkku -> schalten auf PV, VerbraucherNetz -> schalten auf Netz, VerbraucherPVundNetz -> zwischen 6-22 Uhr auf PV sonst Netz 
                if self.SkriptWerte["WrMode"] == self.Akkumode and switchToInverterAllowed():
                    self.aktualMode = schalteRelaisAufPv()
                elif self.SkriptWerte["WrMode"] == self.NetzMode and switchToUtiliyAllowed():
                    # prüfen ob alle WR vom Netz versorgt werden
                    if tmpglobalEffektaData["InputVoltageAnd"] == True:
                        self.aktualMode = schalteRelaisAufNetz()
            elif switchToInverterAllowed():
                # Wir resetten die Variable hier auch damit man durch aus und einchalten von PowerSaveMode das Umschalten auf Netz wieder frei gibt.
                self.aufNetzSchaltenErlaubt = True
                self.aktualMode = schalteRelaisAufPv()
                if self.aktualMode == self.OutputVoltageError:
                    self.aufPvSchaltenErlaubt = False
        elif switchToUtiliyAllowed():
            self.aktualMode = schalteRelaisAufNetz()

    def wetterPrognoseMorgenSchlecht(self):
        # Wir wollen abschätzen ob wir auf Netz schalten müssen dazu soll abends geprüft werden ob noch genug energie für die Nacht zur verfügung steht
        # Dazu wird geprüft wie das Wetter (Sonnenstunden) am nächsten Tag ist und dementsprechend früher oder später umgeschaltet.
        # Wenn das Wetter am nächsten Tag schlecht ist macht es keinen Sinn den Akku leer zu machen und dann im Falle einer Unterspannung vom Netz laden zu müssen.
        # Die Prüfung ist nur Abends aktiv da man unter Tags eine andere Logig haben möchte.
        # In der Sommerzeit löst now.hour = 17 um 18 Uhr aus, In der Winterzeit dann um 17 Uhr
        if "Tag_1" in self.localDeviceData["Wetter"]:
            if self.localDeviceData["Wetter"]["Tag_1"] != None:
                if self.localDeviceData["Wetter"]["Tag_1"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"]:
                    return True
            else:
                self.myPrint(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")
            return False

    def wetterPrognoseHeuteUndMorgenSchlecht(self):
        if "Tag_0" in self.localDeviceData["Wetter"] and "Tag_1" in self.localDeviceData["Wetter"]:
            if self.localDeviceData["Wetter"]["Tag_0"] != None and self.localDeviceData["Wetter"]["Tag_1"] != None:
                if self.localDeviceData["Wetter"]["Tag_0"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"] and self.localDeviceData["Wetter"]["Tag_1"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"]:
                    return True
            else:
                self.myPrint(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")
        return False

    def akkuStandAusreichend(self):
        return self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] < (self.SkriptWerte["verbrauchNachtAkku"] + self.SkriptWerte["MinSoc"])

    def initInverter(self):
        if self.configuration["initModeEffekta"] == "Auto":
            self.autoInitInverter()
        elif self.configuration["initModeEffekta"] == "Akku":
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.SkriptWerte["AutoMode"] = False
        elif self.configuration["initModeEffekta"] == "Netz":
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.SkriptWerte["AutoMode"] = False
        else:
            raise Exception("Unknown initModeEffekta given! Check configurationFile!")
        self.sendeMqtt = True

    def myPrint(self, msgType, msg):
        # convert LOGGER.INFO -> "info" and concat it to topic
        msgTypeSegment = str(msgType)
        msgTypeSegment = msgTypeSegment.split(".")[1]
        msgTypeSegment = msgTypeSegment.lower()
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + msgTypeSegment, msg, globalPublish = True, enableEcho = False)
        self.logger.message(msgType, self, msg)

    def autoInitInverter(self):
        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] == SocMeter.InitAkkuProz:
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz mit Laden. SOC == InitWert")
            self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
        elif 0 <= self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] < self.SkriptWerte["schaltschwelleNetzLadenaus"]:
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz mit Laden")
            self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
        elif self.SkriptWerte["schaltschwelleNetzLadenaus"] <= self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] < self.SkriptWerte["schaltschwelleNetzSchlechtesWetter"]:
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz ohne Laden")
        elif self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"]:
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Akku") 

    def handleMessage(self, message):
        """
        sort the incoming msg to the localDeviceData variable
        handle expectedDevicesPresent variable
        set setable values wich are received global
        """

        # check if its our own topic
        if self.createOutTopic(self.getObjectTopic()) in message["topic"]:
            # we use it and unsubscribe
            self.SkriptWerte = message["content"]
            self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
            # We set the timer because it is possible that the timer is not set yet and the it raise an exc
            self.timer(name = "timeoutMqtt", timeout = 30)
            self.timer(name = "timeoutMqtt", remove = True)
            self.localDeviceData["initialMqttTimeout"] = True
        else:
            # check if the incoming value is part of self.setableSkriptWerte and if true then take the new value
            for key in self.setableSkriptWerte:
                if key in message["content"]:
                    if type(self.SkriptWerte[key]) == float and type(message["content"][key]) == int:
                        message["content"][key] = float(message["content"][key])
                    if type(self.SkriptWerte[key]) == int and type(message["content"][key]) == float:
                        message["content"][key] = int(message["content"][key])
                    try:
                        if type(message["content"][key]) == type(self.SkriptWerte[key]):
                            self.SkriptWerte[key] = message["content"][key]
                            self.sendeMqtt = True
                        else:
                            self.logger.error(self, "Wrong datatype globally received.")
                    except:
                        self.logger.error(self, "Wrong datatype globally received.")

            if message["content"] in self.manualCommands:
                self.sendeMqtt = True
                self.SkriptWerte["AutoMode"] = False
                self.logger.info(self, "Die Anlage wurde auf Manuell gestellt")
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

            # check if a expected device sended a msg and store it
            for key in self.expectedDevices:
                if key in message["topic"]:
                    self.localDeviceData[key] = message["content"]

            # check if all expected devices sent data
            if self.localDeviceData["expectedDevicesPresent"] == False:
                # set expectedDevicesPresent. If a device is not present we reset the value
                self.localDeviceData["expectedDevicesPresent"] = True
                # check if a expected device sended a msg and store it
                for key in self.expectedDevices:
                    # check if all devices are present
                    if not (key in self.localDeviceData):
                        self.localDeviceData["expectedDevicesPresent"] = False

    def threadInitMethod(self):
        self.tagsIncluded(["managedEffektas", "initModeEffekta", "socMonitorName", "bmsName", "relaisNames"])
        # Threadnames we have to wait for a initial message. The worker need this data.
        self.expectedDevices = []
        self.expectedDevices.append(self.configuration["socMonitorName"])
        self.expectedDevices.append(self.configuration["bmsName"])
        # add managedEffekta List, funktion getLinkedEffektaData nedds this data
        self.expectedDevices += self.configuration["managedEffektas"]

        # init some variables
        self.localDeviceData = {"expectedDevicesPresent": False, "initialMqttTimeout": False, "linkedEffektaData":{}, "Wetter":{}}
        # init lists of direct setable values, sensors or commands
        self.setableSlider = {"schaltschwelleAkkuTollesWetter":20.0, "schaltschwelleAkkuRussia":100.0, "schaltschwelleNetzRussia":80.0, "NetzSchnellladenRussia":65.0, "schaltschwelleAkkuSchlechtesWetter":45.0, "schaltschwelleNetzSchlechtesWetter":30.0}
        self.niceNameSlider = {"schaltschwelleAkkuTollesWetter":"Akku gutes Wetter", "schaltschwelleAkkuRussia":"Akku USV", "schaltschwelleNetzRussia":"Netz USV", "NetzSchnellladenRussia":"Laden USV", "schaltschwelleAkkuSchlechtesWetter":"Akku schlechtes Wetter", "schaltschwelleNetzSchlechtesWetter":"Netz schlechtes Wetter"}
        self.setableSwitch = {"Akkuschutz":False, "RussiaMode": False, "PowerSaveMode" : False, "AutoMode": False}
        self.sensorList = {"WrNetzladen":False,  "Error":False, "WrMode":"", "schaltschwelleAkku":100.0, "schaltschwelleNetz":20.0}
        self.manualCommands = ["NetzSchnellLadenEin", "NetzLadenEin", "NetzLadenAus", "WrAufNetz", "WrAufAkku"]
        # (keys of self.SkriptWerte) - self.setableSkriptWerte = nonsetable or internal currentValues
        self.SkriptWerte = {}
        self.SkriptWerte.update(self.setableSlider)
        self.SkriptWerte.update(self.setableSwitch)
        self.SkriptWerte.update(self.sensorList)
        self.setableSkriptWerte = []
        self.setableSkriptWerte += list(self.setableSlider.keys())
        self.setableSkriptWerte += list(self.setableSwitch.keys())
        self.InitialInitWr = True
        self.EntladeFreigabeGesendet = False
        self.NetzLadenAusGesperrt = False
        self.ResetSocSended = False

        # init some constants
        self.Akkumode = "Akku"
        self.NetzMode = "Netz"
        self.initTransferRelais()

        # subscribe global to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        # subscribe Global to get commands from extern
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)

        for device in self.expectedDevices:
            self.mqttSubscribeTopic(self.createOutTopicFilter(self.createProjectTopic(device)), globalSubscription = False)
        for device in self.configuration["managedEffektas"]:
            self.mqttSubscribeTopic(self.createOutTopicFilter(self.createProjectTopic(device)), globalSubscription = False)

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self, self.sensorList)
        self.homeAutomation.mqttDiscoverySelector(self, self.manualCommands, niceName = "Pv Cmd")
        self.homeAutomation.mqttDiscoveryInputNumberSlider(self, self.setableSlider, nameDict = self.niceNameSlider)
        self.homeAutomation.mqttDiscoverySwitch(self, self.setableSwitch)


    def threadMethod(self):
        self.sendeMqtt = False

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass
            self.handleMessage(newMqttMessageDict)

        # check Timer, delete it and remember internally
        if not self.localDeviceData["initialMqttTimeout"]:
            if self.timer(name = "timeoutMqtt", timeout = 30):
                self.timer(name = "timeoutMqtt", remove = True)
                self.localDeviceData["initialMqttTimeout"] = True
                self.logger.info(self, "MQTT init timeout.")


        # if all devices has sended its work data then we will run the worker
        if self.localDeviceData["expectedDevicesPresent"] and self.localDeviceData["initialMqttTimeout"]:
            self.manageLogicalLinkedEffektaData()
            now = datetime.datetime.now()

            self.passeSchaltschwellenAn()

            if self.InitialInitWr:
                self.InitialInitWr = False
                self.initInverter()


            # Wir prüfen als erstes ob die Freigabe vom BMS da ist und kein Akkustand Error vorliegt
            if self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"] == True and self.SkriptWerte["Error"] == False:
                # Wir wollen erst prüfen ob das skript automatisch schalten soll.
                if self.SkriptWerte["AutoMode"]:

                    # Wir prüfen ob wir wegen zu wenig prognostiziertem Ertrag auf Netz schalten müssen
                    if now.hour >= 17 and now.hour < 23:
                        if self.wetterPrognoseMorgenSchlecht() and self.akkuStandAusreichend():
                            #self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.SkriptWerte["Akkuschutz"] = True
                            self.myPrint(Logger.LOG_LEVEL.INFO, "Sonnen Stunden < %ih -> schalte auf Netz." %self.SkriptWerte["wetterSchaltschwelleNetz"])

                    if now.hour >= 12 and now.hour < 23:
                        if self.wetterPrognoseHeuteUndMorgenSchlecht() and self.akkuStandAusreichend():
                            #self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.SkriptWerte["Akkuschutz"] = True
                            self.myPrint(Logger.LOG_LEVEL.INFO, "Sonnen Stunden < %ih -> schalte auf Netz." %self.SkriptWerte["wetterSchaltschwelleNetz"])

                    self.passeSchaltschwellenAn()

                    # todo self.SkriptWerte["Akkuschutz"] = False Über Wetter?? Was ist mit "Error: Ladestand weicht ab"
                    if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["AkkuschutzAbschalten"]:
                        self.SkriptWerte["Akkuschutz"] = False

                    # behandeln vom Laden in RussiaMode (USV)
                    if self.SkriptWerte["RussiaMode"]:
                        self.NetzLadenAusGesperrt = True
                        if self.SkriptWerte["WrNetzladen"] == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= (self.SkriptWerte["schaltschwelleNetz"] - self.SkriptWerte["verbrauchNachtNetz"]):
                            self.schalteAlleWrNetzSchnellLadenEin(self.configuration["managedEffektas"])
                        if self.SkriptWerte["WrNetzladen"] == True and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleNetz"]:
                            self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])

                    if self.SkriptWerte["WrMode"] == self.Akkumode:
                        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= self.SkriptWerte["schaltschwelleNetz"]:
                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.myPrint(Logger.LOG_LEVEL.INFO, "%iP erreicht -> schalte auf Netz." %self.SkriptWerte["schaltschwelleNetz"])  
                    elif self.SkriptWerte["WrMode"] == self.NetzMode:
                        if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleAkku"]:
                            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
                            self.NetzLadenAusGesperrt = False
                            self.myPrint(Logger.LOG_LEVEL.INFO, "%iP erreicht -> Schalte auf Akku"  %self.SkriptWerte["schaltschwelleAkku"])
                    else:
                        # Wr Mode nicht bekannt
                        self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.ERROR, "WrMode nicht bekannt! Schalte auf Netz")


                    # Wenn Akkuschutz an ist und die schaltschwelle NetzLadenEin erreicht ist, dann laden wir vom Netz
                    if self.SkriptWerte["WrNetzladen"] == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] <= self.SkriptWerte["schaltschwelleNetzLadenein"]:
                        self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.INFO, "Schalte auf Netz mit laden")


                    # Wenn das Netz Laden durch eine Unterspannungserkennung eingeschaltet wurde schalten wir es aus wenn der Akku wieder 10% hat
                    if self.SkriptWerte["WrNetzladen"] == True and self.NetzLadenAusGesperrt == False and self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleNetzLadenaus"]:
                        self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.INFO, "NetzLadenaus %iP erreicht -> schalte Laden aus." %self.SkriptWerte["schaltschwelleNetzLadenaus"])


                # Wenn das BMS die entladefreigabe wieder erteilt dann reseten wir EntladeFreigabeGesendet damit das nachste mal wieder gesendet wird
                self.EntladeFreigabeGesendet = False
            elif self.EntladeFreigabeGesendet == False:
                self.EntladeFreigabeGesendet = True
                self.schalteAlleWrAufNetzMitNetzladen(self.configuration["managedEffektas"])
                # Falls der Akkustand zu hoch ist würde nach einer Abschaltung das Netzladen gleich wieder abgeschaltet werden das wollen wir verhindern
                self.myPrint(Logger.LOG_LEVEL.ERROR, f'Schalte auf Netz mit laden. Trigger-> BMS: {not self.localDeviceData[self.configuration["bmsName"]]["BmsEntladeFreigabe"]}, Error: {self.SkriptWerte["Error"]}')
                if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleNetzLadenaus"]:
                    # Wenn eine Unterspannnung SOC > schaltschwelleNetzLadenaus ausgelöst wurde dann stimmt mit dem SOC etwas nicht und wir wollen verhindern, dass die Ladung gleich wieder abgestellt wird
                    self.NetzLadenAusGesperrt = True
                    self.SkriptWerte["Akkuschutz"] = True
                    self.myPrint(Logger.LOG_LEVEL.ERROR, f'Ladestand weicht ab, UnterSpannung BMS bei {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}%')
                # wir setzen einen error weil das nicht plausibel ist und wir hin und her schalten sollte die freigabe wieder kommen
                # wir wollen den Akku erst bis 100 P aufladen 
                if self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"] >= self.SkriptWerte["schaltschwelleAkkuTollesWetter"]:
                    self.SkriptWerte["Error"] = True
                    # Wir setzen den Error zurück wenn der Inverter auf Floatmode umschaltet. Wenn diese bereits gesetzt ist dann müssen wir das Skript beenden da der Error sonst gleich wieder zurück gesetzt werden würde
                    if self.localDeviceData["linkedEffektaData"]["FloatingModeOr"] == True:
                        raise Exception("SOC Wert unplaulibel und FloatMode Inverter aktiv!") 
                    self.myPrint(Logger.LOG_LEVEL.ERROR, f'Ladestand unplausibel, Unterspannung BMS bei {self.localDeviceData[self.configuration["socMonitorName"]]["Prozent"]}%')
                self.sendeMqtt = True

            self.passeSchaltschwellenAn()

            # Zum debuggen wollen wir das Relais nicht laufen ansteuern, darum warten wir
            if self.timer(name = "timeoutTransferRelais", timeout = 10*60):
                self.manageTransferRelais()

            if self.sendeMqtt == True: 
                self.sendeMqtt = False
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SkriptWerte, globalPublish = True, enableEcho = False)

        else:
            if self.timer(name = "timeoutExpectedDevices", timeout = 10*60):
                self.myPrint(Logger.LOG_LEVEL.ERROR, "Es haben sich nicht alle erwarteten Devices gemeldet!")
                for device in self.expectedDevices:
                    if not device in self.localDeviceData:
                        self.myPrint(Logger.LOG_LEVEL.ERROR, f"Device: {device} fehlt!")
                raise Exception("Some devices are missing after timeout!") 


    def threadBreak(self):
        time.sleep(0.5)