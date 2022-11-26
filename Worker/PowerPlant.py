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
    classdocs
    '''


    def passeSchaltschwellenAn(self):
        #SOC Schaltschwellen in Prozent
        self.SkriptWerte["schaltschwelleNetzLadenaus"] = 11.0
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
        self.sendEffektaData(EffektaController.getCmdSwitchUtilityFastChargeOn()(), effektas)
        self.SkriptWerte["WrNetzladen"] = True
        # Wir müssen hier auf Manuell schalten damit das Skrip nich gleich zurückschaltet
        self.SkriptWerte["SkriptMode"] = "Manual"
        self.SkriptWerte["WrMode"] = self.NetzMode
        self.sendeSkriptDaten()
        self.myPrint(Logger.LOG_LEVEL.INFO, "Schnellladen vom Netz wurde aktiviert!")
        self.myPrint(Logger.LOG_LEVEL.INFO, "Die Anlage wurde auf manuell gestellt!")
        self.sendeMqtt = True

    def resetSocMonitor(self):
        # @todo topic und evt auch msg ermitteln
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
            self.ResetSocSended = True
        else:
            self.ResetSocSended = False
    def initInverter(self):
        if self.configuration["initModeEffekta"] == "Auto":
            if self.localDeviceData["SocMonitor"]["Prozent"] == SocMeter.InitAkkuProz:
                # if the value is still (after getting work data from soc) on initAkkuProz we fallback on "Netz"
                self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            else:
                self.autoInitInverter()
                self.sendeMqtt = True
        elif self.configuration["initModeEffekta"] == "Akku":
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode
            self.SkriptWerte["SkriptMode"] = "Manual"
        elif self.configuration["initModeEffekta"] == "Netz":
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            # we disable auto mode because user want to start up in special mode


    def myPrint(self, msgType, msg):
        # convert LOGGER.INFO -> "info"
        msgTypeSegment = str(msgType)
        msgTypeSegment = msgTypeSegment.split(".")[1]
        msgTypeSegment = msgTypeSegment.lower()
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/" + msgTypeSegment, msg, globalPublish = True, enableEcho = False)
        self.logger.message(msgType, self, msg)


    def autoInitInverter(self):
        if 0 < self.localDeviceData["SocMonitor"]["Prozent"] < self.SkriptWerte["schaltschwelleNetzLadenaus"]:
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz mit Laden")
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
        elif self.SkriptWerte["schaltschwelleNetzLadenaus"] <= self.localDeviceData["SocMonitor"]["Prozent"] < self.SkriptWerte["schaltschwelleNetzSchlechtesWetter"]:
            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Netz ohne Laden")                     
        elif self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["schaltschwelleAkkuSchlechtesWetter"]:
            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
            self.myPrint(Logger.LOG_LEVEL.INFO, "AutoInit: Schalte auf Akku") 


    def handleMessage(self, message):
        """
        sort the incoming msg to the localDeviceData variable and handle expectedDevicesPresent variable
        """
        if self.createActualTopic(self.getObjectTopic()) in message["topic"]:
            # if old own data received we use it and unsubscribe
            self.SkriptWerte = message["content"]
            self.mqttUnSubscribeTopic(self.createActualTopic(self.getObjectTopic()))
            self.timer(name = "timeoutMqtt", remove = True)
            self.localDeviceData["initialMqttTimeout"] = True
        else:
            # set expectedDevicesPresent. If a device is not present we reset the value
            self.localDeviceData["expectedDevicesPresent"] = True
            # check if a expected device sended a msg and store it
            for key in self.expectedDevices:
                if key in message["topic"]:
                    self.localDeviceData[key] = message["content"]
                # check if all devices except effektas are present
                if not (key in self.localDeviceData):
                    self.localDeviceData["expectedDevicesPresent"] = False


    def threadInitMethod(self):
        self.tagsIncluded(["managedEffektas", "initModeEffekta"])
        self.localDeviceData = {"expectedDevicesPresent": False, "initialMqttTimeout": False}
        self.SkriptWerte = {"WrNetzladen":False, "Akkuschutz":False, "RussiaMode": False, "Error":False, "WrMode":"", "SkriptMode":"Auto", "PowerSaveMode":False, "schaltschwelleAkku":100.0, "schaltschwelleNetz":20.0, "schaltschwelleAkkuTollesWetter":20.0, "schaltschwelleAkkuRussia":100.0, "schaltschwelleNetzRussia":80.0, "schaltschwelleAkkuSchlechtesWetter":45.0, "schaltschwelleNetzSchlechtesWetter":30.0}
        # Threadnames we have to wait for a initial message. The worker need this data.
        self.expectedDevices = ["BMS", "SocMonitor"]
        # init some variables
        self.InitialInitWr = True
        self.EntladeFreigabeGesendet = False
        self.NetzLadenAusGesperrt = False
        # init some constants
        self.Akkumode = "Akku"
        self.NetzMode = "Netz"
        # subscribe global to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createActualTopic(self.getObjectTopic()), globalSubscription = True)

        for device in self.expectedDevices:
            self.mqttSubscribeTopic(self.createOutTopicFilter(self.createProjectTopic(device)), globalSubscription = False)
        for device in self.configuration["managedEffektas"]:
            self.mqttSubscribeTopic(self.createOutTopicFilter(self.createProjectTopic(device)), globalSubscription = False)

    def threadMethod(self):
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
            #if Supporter.timer(name = "timeoutMqtt", timeout = 30):
            if self.timer(name = "timeoutMqtt", timeout = 3):
                self.timer(name = "timeoutMqtt", remove = True)
                self.localDeviceData["initialMqttTimeout"] = True
                self.logger.info(self, "MQTT init timeout.")

        # if all devices has sended its work data then we will run the worker
        if self.localDeviceData["expectedDevicesPresent"] and self.localDeviceData["initialMqttTimeout"]:
            now = datetime.datetime.now()
            self.sendeMqtt = False

            self.passeSchaltschwellenAn()

            if self.InitialInitWr:
                self.InitialInitWr = False
                self.initInverter()


            # Wir setzen den Error bei 100 prozent zurück. In der Hoffunng dass nicht immer 100 prozent vom BMS kommen dieses fängt aber bei einem Neustart bei 0 proz an.
            if self.localDeviceData["SocMonitor"]["Prozent"] >= 100.0:
                self.SkriptWerte["Error"] = False


            # Wir prüfen als erstes ob die Freigabe vom BMS da ist und kein Akkustand Error vorliegt
            if self.localDeviceData["BMS"]["BmsEntladeFreigabe"] == True and self.SkriptWerte["Error"] == False:
                # Wir wollen erst prüfen ob das skript automatisch schalten soll.
                if self.SkriptWerte["SkriptMode"] == "Auto":
                    # Wir wollen abschätzen ob wir auf Netz schalten müssen dazu soll abends geprüft werden ob noch genug energie für die Nacht zur verfügung steht
                    # Dazu wird geprüft wie das Wetter (Sonnenstunden) am nächsten Tag ist und dementsprechend früher oder später umgeschaltet.
                    # Wenn das Wetter am nächsten Tag schlecht ist macht es keinen Sinn den Akku leer zu machen und dann im Falle einer Unterspannung vom Netz laden zu müssen.
                    # Die Prüfung ist nur Abends aktiv da man unter Tags eine andere Logig haben möchte.
                    # In der Sommerzeit löst now.hour = 17 um 18 Uhr aus, In der Winterzeit dann um 17 Uhr
                    if now.hour >= 17 and now.hour < 23:
                    #if Zeit >= 17 and Zeit < 23:
                        if "Tag_1" in self.localDeviceData["Wetter"]:
                            if self.localDeviceData["Wetter"]["Tag_1"] != None:
                                if self.localDeviceData["Wetter"]["Tag_1"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"]:
                                # Wir wollen den Akku schonen weil es nichts bringt wenn wir ihn leer machen
                                    if self.localDeviceData["SocMonitor"]["Prozent"] < (self.SkriptWerte["verbrauchNachtAkku"] + self.SkriptWerte["MinSoc"]):
                                        if self.SkriptWerte["WrMode"] == self.Akkumode:
                                            # todo ist das so sinnvoll. Bestand
                                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                                            self.SkriptWerte["Akkuschutz"] = True
                                            self.myPrint(Logger.LOG_LEVEL.INFO, "Sonne morgen < %ih -> schalte auf Netz." %self.SkriptWerte["wetterSchaltschwelleNetz"])
                            else:
                                self.myPrint(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")
                    # In der Sommerzeit löst now.hour = 17 um 18 Uhr aus, In der Winterzeit dann um 17 Uhr
                    if now.hour >= 12 and now.hour < 23:
                    #if Zeit >= 17 and Zeit < 23:
                        if "Tag_0" in self.localDeviceData["Wetter"] and "Tag_1" in self.localDeviceData["Wetter"]:
                            if self.localDeviceData["Wetter"]["Tag_0"] != None and self.localDeviceData["Wetter"]["Tag_1"] != None:
                                if self.localDeviceData["Wetter"]["Tag_0"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"] and self.localDeviceData["Wetter"]["Tag_1"]["Sonnenstunden"] <= self.SkriptWerte["wetterSchaltschwelleNetz"]:
                                # Wir wollen den Akku schonen weil es nichts bringt wenn wir ihn leer machen
                                    if self.localDeviceData["SocMonitor"]["Prozent"] < (self.SkriptWerte["verbrauchNachtAkku"] + self.SkriptWerte["MinSoc"]):
                                        if self.SkriptWerte["WrMode"] == self.Akkumode:
                                            # todo ist das so sinnvoll. Bestand
                                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                                            self.SkriptWerte["Akkuschutz"] = True
                                            self.myPrint(Logger.LOG_LEVEL.INFO, "Sonne heute und morgen < %ih -> schalte auf Netz." %self.SkriptWerte["wetterSchaltschwelleNetz"])
                            else:
                                self.myPrint(Logger.LOG_LEVEL.ERROR, "Keine Wetterdaten!")

                    self.passeSchaltschwellenAn()

                    # todo self.SkriptWerte["Akkuschutz"] = False Über Wetter?? Was ist mit "Error: Ladestand weicht ab"
                    if self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["AkkuschutzAbschalten"]:
                        self.SkriptWerte["Akkuschutz"] = False


                    if self.SkriptWerte["WrMode"] == self.Akkumode:
                        if self.localDeviceData["SocMonitor"]["Prozent"] <= self.SkriptWerte["MinSoc"]:
                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.myPrint(Logger.LOG_LEVEL.INFO, "MinSOC %iP erreicht -> schalte auf Netz." %self.SkriptWerte["MinSoc"])
                        elif self.localDeviceData["SocMonitor"]["Prozent"] <= self.SkriptWerte["schaltschwelleNetz"]:
                            self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                            self.myPrint(Logger.LOG_LEVEL.INFO, "%iP erreicht -> schalte auf Netz." %self.SkriptWerte["schaltschwelleNetz"])  
                    elif self.SkriptWerte["WrMode"] == self.NetzMode:
                        if self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["schaltschwelleAkku"]:
                            self.schalteAlleWrAufAkku(self.configuration["managedEffektas"])
                            self.NetzLadenAusGesperrt = False
                            self.myPrint(Logger.LOG_LEVEL.INFO, "%iP erreicht -> Schalte auf Akku"  %self.SkriptWerte["schaltschwelleAkku"])
                    else:
                        # Wr Mode nicht bekannt
                        self.schalteAlleWrAufNetzOhneNetzLaden(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.ERROR, "WrMode nicht bekannt! Schalte auf Netz")


                    # Wenn Akkuschutz an ist und die schaltschwelle NetzLadenEin erreicht ist, dann laden wir vom Netz
                    if self.SkriptWerte["WrNetzladen"] == False and self.SkriptWerte["Akkuschutz"] == True and self.localDeviceData["SocMonitor"]["Prozent"] <= self.SkriptWerte["schaltschwelleNetzLadenein"]:
                        self.schalteAlleWrNetzLadenEin(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.INFO, "Schalte auf Netz mit laden")


                    # Wenn das Netz Laden durch eine Unterspannungserkennung eingeschaltet wurde schalten wir es aus wenn der Akku wieder 10% hat
                    if self.SkriptWerte["WrNetzladen"] == True and self.NetzLadenAusGesperrt == False and self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["schaltschwelleNetzLadenaus"]:
                        self.schalteAlleWrNetzLadenAus(self.configuration["managedEffektas"])
                        self.myPrint(Logger.LOG_LEVEL.INFO, "NetzLadenaus %iP erreicht -> schalte Laden aus." %self.SkriptWerte["schaltschwelleNetzLadenaus"])


                # Wenn das BMS die entladefreigabe wieder erteilt dann reseten wir EntladeFreigabeGesendet damit das nachste mal wieder gesendet wird
                self.EntladeFreigabeGesendet = False
            elif self.EntladeFreigabeGesendet == False:
                self.EntladeFreigabeGesendet = True
                self.schalteAlleWrAufNetzMitNetzladen(self.configuration["managedEffektas"])
                # Falls der Akkustand zu hoch ist würde nach einer Abschaltung das Netzladen gleich wieder abgeschaltet werden das wollen wir verhindern
                self.myPrint(Logger.LOG_LEVEL.ERROR, f'Schalte auf Netz mit laden. Trigger-> BMS: {not self.localDeviceData["BMS"]["BmsEntladeFreigabe"]}, Error: {self.SkriptWerte["Error"]}')
                if self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["schaltschwelleNetzLadenaus"]:
                    # Wenn eine Unterspannnung SOC > schaltschwelleNetzLadenaus ausgelöst wurde dann stimmt mit dem SOC etwas nicht und wir wollen verhindern, dass die Ladung gleich wieder abgestellt wird
                    self.NetzLadenAusGesperrt = True
                    self.SkriptWerte["Akkuschutz"] = True
                    self.myPrint(Logger.LOG_LEVEL.ERROR, "Ladestand weicht ab")
                # wir setzen einen error weil das nicht plausibel ist und wir hin und her schalten sollte die freigabe wieder kommen
                # wir wollen den Akku erst bis 100 P aufladen 
                if self.localDeviceData["SocMonitor"]["Prozent"] >= self.SkriptWerte["schaltschwelleAkkuTollesWetter"]:
                    self.SkriptWerte["Error"] = True
                    self.myPrint(Logger.LOG_LEVEL.ERROR, "Ladestand nicht plausibel")
                self.sendeMqtt = True

            self.passeSchaltschwellenAn()

            if self.sendeMqtt == True: 
                self.sendeMqtt = False
                self.mqttPublish(self.createActualTopic(self.getObjectTopic()), self.SkriptWerte, globalPublish = True, enableEcho = False)



    def threadBreak(self):
        time.sleep(5)