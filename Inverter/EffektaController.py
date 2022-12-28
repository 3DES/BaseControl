import time
import datetime
import json
from Base.ThreadObject import ThreadObject


class EffektaController(ThreadObject):
    '''
    classdocs
    '''
    VerbraucherNetz = "POP00"       # load prio 00=Netz, 02=Batt, 01=PV und Batt, wenn PV verfügbar ansonsten Netz
    VerbraucherAkku = "POP02"       # load prio 00=Netz, 02=Batt, 01=PV und Batt, wenn PV verfügbar ansonsten Netz
    BattLeer = "PSDV43.0"
    BattWiederEntladen = "PBDV48.0"
    NetzSchnellLadestrom = "MUCHGC030"
    NetzErhaltungsLadestrom = "MUCHGC002"
    chargePrioNetzPV = "PCP02"             # charge prio 02=Netz und pv, 03=pv
    chargePrioPV = "PCP03"             # charge prio 02=Netz und pv, 03=pv


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)


    """
    @todo kommentar bearbeiten. zum besseren Vergleich wurde er nur erweitert
    die aktuellen Funktionen schalten nicht mehr aktiv sondern richten nur noch das cmd her
    getCmdSwitchToBattery ehem.                   schalteAlleWrAufAkku()              Schaltet alle Wr auf Akku, setzt die Unterspannungserkennung des Wr ausser Kraft
    getCmdSwitchUtilityChargeOff ehem.            schalteAlleWrNetzLadenAus()         Schaltet das Laden auf PV
    getCmdSwitchUtilityChargeOn ehem.             schalteAlleWrNetzLadenEin()         Schaltet das Laden auf PV+Netz, schaltet die Verbraucher auf Netz, setzt den Netz Ladstrom auf NetzErhaltungsLadestrom
    getCmdSwitchUtilityFastChargeOn ehem          schalteAlleWrNetzSchnellLadenEin()  Schaltet das Laden auf PV+Netz, schaltet die Verbraucher auf Netz, setzt den Netz Ladstrom auf NetzSchnellLadestrom, schaltet das Skript auf Manuell
    getCmdSwitchToUtility ehem                    schalteAlleWrAufNetzOhneNetzLaden() Schaltet alle Wr auf Netz, setzt die Unterspannungserkennung des Wr ausser Kraft
    getCmdSwitchToUtilityWithUvDetection ehem     schalteAlleWrAufNetzMitNetzladen()  Schaltet alle Wr auf Netz, setzt die Unterspannungserkennung des Wr auf aktiv
    """
    

    @classmethod
    def getSetValueKeys(cls, cmd, value = "", extern = False):
        return {"cmd":cmd, "value":value, "success": False, "extern":extern}

    @classmethod
    def getQueryKeys(cls, cmd, extern = False):
        return {"cmd":cmd, "response":"", "extern":extern}

    @classmethod
    def getSetValueDict(cls, cmd, value = "", extern = False):
        return {"setValue":cls.getSetValueKeys(cmd, value, extern)}

    @classmethod
    def getQueryDict(cls, cmd, extern = False):
        return {"query":cls.getQueryKeys(cmd, extern)}

    @classmethod
    def getCmdSwitchToBattery(cls):
        parList = []
        parList.append(cls.getSetValueKeys(cls.BattLeer))
        parList.append(cls.getSetValueKeys(cls.BattWiederEntladen))
        parList.append(cls.getSetValueKeys(cls.VerbraucherAkku))
        parList.append(cls.getSetValueKeys(cls.chargePrioPV))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchUtilityChargeOff(cls):
        return cls.getSetValueDict(cls.chargePrioPV)

    @classmethod
    def getCmdSwitchUtilityChargeOn(cls):
        parList = []
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        # @todo kleinsten strom automatisch ermitteln
        parList.append(cls.getSetValueKeys(cls.NetzErhaltungsLadestrom))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchUtilityFastChargeOn(cls):
        parList = []
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys(cls.NetzSchnellLadestrom))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchToUtility(cls):
        parList = []
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys(cls.BattLeer))
        parList.append(cls.getSetValueKeys(cls.BattWiederEntladen))
        parList.append(cls.getSetValueKeys(cls.chargePrioPV))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchToUtilityWithUvDetection(cls):
        parList = []
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys("PBDV52.0"))
        parList.append(cls.getSetValueKeys("PSDV48.0"))
        parList.append(cls.getSetValueKeys(cls.NetzErhaltungsLadestrom))
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        return {"setValue":parList}

    @classmethod
    def getLinkedEffektaData(cls, EffektaData):
        """
        returns given Effekta data with logical link
        given data is a dict with one or more Effektas {"effekta_A":{Data}, "effekta_B":{Data}}
        """
        globalEffektaData = {"FloatingModeOr" : False, "OutputVoltageHighOr" : False, "InputVoltageAnd" : True, "OutputVoltageHighAnd" : True, "OutputVoltageLowAnd" : True, "ErrorPresentOr" : False}
        for name in list(EffektaData.keys()):
            floatmode = list(EffektaData[name]["DeviceStatus2"])
            if floatmode[0] == "1":
                globalEffektaData["FloatingModeOr"] = True
            if float(EffektaData[name]["Netzspannung"]) < 210.0:
                globalEffektaData["InputVoltageAnd"] = False
            if float(EffektaData[name]["AcOutSpannung"]) < 210.0:
                globalEffektaData["OutputVoltageHighAnd"] = False 
            if float(EffektaData[name]["AcOutSpannung"]) > 25.0:
                globalEffektaData["OutputVoltageLowAnd"] = False
                globalEffektaData["OutputVoltageHighOr"] = True
            if EffektaData[name]["ActualMode"] == "F":
                globalEffektaData["ErrorPresentOr"] = True
        return globalEffektaData

    def updateChargeValues(self):
        self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMUCHGCR"), globalPublish = False, enableEcho = False)

    def checkWerteSprung(self, newValue, oldValue, percent, minVal, maxVal, minAbs = 0):
        
        # Diese Funktion prüft, dass der neue Wert innerhalb der angegebenen maxVal maxVal Grenzen und ausserhalb der angegebenen Prozent Grenze
        # Diese Funktion wird verwendet um kleine Wertsprünge rauszu Filtern und Werte Grenzen einzuhalten

        if newValue == oldValue == 0:
            #myPrint("wert wird nicht uebernommen")
            return False
            
        percent = percent * 0.01
        valuePercent = abs(oldValue) * percent
        
        if valuePercent < minAbs:
            valuePercent = minAbs
            
        minPercent = oldValue - valuePercent
        maxPercent = oldValue + valuePercent
        
        if minVal <= newValue <= maxVal and not (minPercent < newValue < maxPercent):
            #myPrint("wert wird uebernommen")
            return True
        else:
            #myPrint("wert wird nicht uebernommen")
            return False


    def threadInitMethod(self):
        self.EffektaData = {"EffektaWerte": {"Netzspannung": 0, "AcOutSpannung": 0, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "", "DailyProduction": 0.0, "CompleteProduction": 0, "BattCapacity": 0, "DeviceStatus2": "", "BattSpannung": 0.0}}
        self.tempDailyProduction = 0.0
        self.timeStamp = time.time()
        self.valideChargeValues = []
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()) + "/#", globalSubscription = True)
        #self.mqttSubscribeTopic(self.createInTopic(self.getClassTopic()) + "/#", globalSubscription = True)

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self, self.EffektaData["EffektaWerte"])
        self.initialMqttSend = True

    def threadMethod(self):
        '''
        supported funktions:
        
        if topic includes "queryExtern" or "setValueExtern" we send a extern query or setValue to the interface. The response 
        will be published global. The msg content have to be the name of the parameter in string type.
        
        we send depending of effekta_Query_Cycle a internal query to the interface. If the response arrives we check all values 
        if there are big changes and publish them global.    
        
        we accept our own msg to get our old values initial.
        
        '''

        effekta_Query_Cycle = 20
        # battEnergyCycle = 8
        # timestampbattEnergyCycle = 0
        # tempDailyDischarge = 0.0
        # tempDailyCharge = 0.0

        if self.timeStamp + effekta_Query_Cycle < time.time():
            self.timeStamp = time.time()
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QPIGS"), globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMOD"), globalPublish = False, enableEcho = False)
            if not self.valideChargeValues:
                # If valideChargeValues is emty we send a query and fill it if effekta answers
                self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMUCHGCR"), globalPublish = False, enableEcho = False)

        self.sendeGlobalMqtt = False

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():

            newMqttMessageDict = self.mqttRxQueue.get(block = False)

            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass


            # First we check if the msg is not from our Interface
            if not (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                # if the msg is not from interface we will send it to the interface, either marked with global or not 
                if "query" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                elif "setValue" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                # from extern we only need the sting of parameter, we build the required msg here
                elif "queryExtern" in newMqttMessageDict["topic"]:
                    self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict(newMqttMessageDict["content"], extern=True), globalPublish = False, enableEcho = False)
                elif "setValueExtern" in newMqttMessageDict["topic"]:
                    self.mqttPublish(self.interfaceInTopics[0], self.getSetValueDict(newMqttMessageDict["content"], extern = True), globalPublish = False, enableEcho = False)
                elif "Netzspannung" in newMqttMessageDict["content"]:
                    # if we get our own Data will overwrite internal data. For initial settings like ...Production
                    self.EffektaData["EffektaWerte"] = newMqttMessageDict["content"]
                    self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
            else:
                # The msg is from our interface
                if "setValue" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["setValue"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"]["setValue"]["success"], globalPublish = True, enableEcho = False)
                elif "query" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["query"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"]["query"]["response"], globalPublish = True, enableEcho = False)
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMUCHGCR" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        # get setable charge values
                        self.valideChargeValues = newMqttMessageDict["content"]["query"]["response"].split()
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMOD" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        if self.EffektaData["EffektaWerte"]["ActualMode"] != newMqttMessageDict["content"]["query"]["response"]:
                            self.sendeGlobalMqtt = True
                            self.EffektaData["EffektaWerte"]["ActualMode"] = newMqttMessageDict["content"]["query"]["response"]
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QPIGS" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        (Netzspannung, Netzfrequenz, AcOutSpannung, AcOutFrequenz, AcOutPowerVA, AcOutPower, AcOutLoadProz, BusVoltage, BattSpannung, BattCharge, BattCapacity, InverterTemp, PvCurrent, PvVoltage, BattVoltageSCC, BattDischarge, DeviceStatus1, BattOffset, EeVersion, PvPower, DeviceStatus2) = newMqttMessageDict["content"]["query"]["response"].split()
                        self.EffektaData["EffektaWerte"]["AcOutSpannung"] = float(AcOutSpannung)

                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["Netzspannung"], int(float(Netzspannung)), 3, -1, 10000):
                            self.EffektaData["EffektaWerte"]["Netzspannung"] = int(float(Netzspannung))
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["AcOutPower"], int(AcOutPower), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["AcOutPower"] = int(AcOutPower)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["PvPower"], int(PvPower), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["PvPower"] = int(PvPower)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattCharge"], int(BattCharge), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattCharge"] = int(BattCharge)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattDischarge"], int(BattDischarge), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattDischarge"] = int(BattDischarge)
                            self.sendeGlobalMqtt = True
                        if self.EffektaData["EffektaWerte"]["DeviceStatus2"] != DeviceStatus2:
                            self.EffektaData["EffektaWerte"]["DeviceStatus2"] = DeviceStatus2
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattSpannung"], float(BattSpannung), 0.5, -1, 100) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattSpannung"] = float(BattSpannung)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattCapacity"], int(BattCapacity), 1, -1, 101) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattCapacity"] = int(BattCapacity)
                            self.sendeGlobalMqtt = True

                        self.tempDailyProduction = self.tempDailyProduction + (int(PvPower) * effekta_Query_Cycle / 60 / 60 / 1000)
                        self.EffektaData["EffektaWerte"]["DailyProduction"] = round(self.tempDailyProduction, 2)

                        # If first data arrived, and software just start up we want to send. Powerplant checks this.
                        if self.initialMqttSend:
                            self.initialMqttSend = False
                            self.sendeGlobalMqtt = True

        now = datetime.datetime.now()
        if now.hour == 23:
            if self.EffektaData["EffektaWerte"]["DailyProduction"] > 0.0:
                self.EffektaData["EffektaWerte"]["CompleteProduction"] = self.EffektaData["EffektaWerte"]["CompleteProduction"] + round(self.EffektaData["EffektaWerte"]["DailyProduction"])
                self.EffektaData["EffektaWerte"]["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
                self.sendeGlobalMqtt = True

        if self.sendeGlobalMqtt:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = True, enableEcho = False)
            self.sendeGlobalMqtt = False
        else:
            pass
            # @todo send aktual values here
            #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)
