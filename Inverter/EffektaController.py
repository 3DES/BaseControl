import time
import datetime
import json
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter
import Logger


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
    fullTextMode = {
        "P" : "Power on mode",
        "S" : "Standby mode",
        "L" : "Line mode",
        "B" : "Battery mode",
        "F" : "Fault mode",
        "H" : "Power saving mode"
    }


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
    def getCombinedEffektaData(cls, EffektaData):
        """
        returns given Effekta data with logical link
        given data is a dict with one or more Effektas {"effekta_A":{Data}, "effekta_B":{Data}}
        """
        globalEffektaData = {"FloatingModeOr" : False, "OutputVoltageHighOr" : False, "InputVoltageAnd" : True, "OutputVoltageHighAnd" : True, "OutputVoltageLowAnd" : True, "ErrorPresentOr" : False}
        currentlyHandledKey = None
        floatmode = None
        try:
            for name in list(EffektaData.keys()):
                currentlyHandledKey = name
                # from "DeviceStatus2" string take first character because it contains the state of the float mode
                floatmode = list(EffektaData[name]["DeviceStatus2"])
                # todo pollen und timeout wenn keine Daten kommen. Es kann sein dass der powerplant die funktion aufruft und der effekta noch keine daten liefert.
                #       if floatmode[0] == "1":
                #          ~~~~~~~~~^^^
                #    IndexError: list index out of range
                if floatmode[0] == "1":
                    globalEffektaData["FloatingModeOr"] = True
                # process all other values from the inverters and combine them
                if float(EffektaData[name]["Netzspannung"]) < 210.0:
                    globalEffektaData["InputVoltageAnd"] = False
                if float(EffektaData[name]["AcOutSpannung"]) < 210.0:
                    globalEffektaData["OutputVoltageHighAnd"] = False 
                if float(EffektaData[name]["AcOutSpannung"]) > 25.0:
                    globalEffektaData["OutputVoltageLowAnd"] = False
                    globalEffektaData["OutputVoltageHighOr"] = True
                if EffektaData[name]["ActualMode"] == "F":
                    globalEffektaData["ErrorPresentOr"] = True
        except Exception as ex:
            Logger.Logger.Logger.error(cls, f"Wir konnten CombinedEffektaData nicht bilden. Exception:{ex}, EffektaData:{EffektaData}, Aktueller key:{currentlyHandledKey}, floatmode:{floatmode}")
        return globalEffektaData

    def updateChargeValues(self):
        self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMUCHGCR"), globalPublish = False, enableEcho = False)

    def threadInitMethod(self):
        self.EffektaData = {"EffektaWerte": {"Netzspannung": 0, "AcOutSpannung": 0, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "", "ActualModeText": "", "DailyProduction": 0.0, "CompleteProduction": 0, "BattCapacity": 0, "DeviceStatus2": "", "BattSpannung": 0.0}}
        self.tempDailyProduction = 0.0
        self.valideChargeValues = []
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()) + "/#", globalSubscription = True)
        #self.mqttSubscribeTopic(self.createInTopic(self.getClassTopic()) + "/#", globalSubscription = True)

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self.EffektaData["EffektaWerte"])
        self.homeAutomation.mqttDiscoverySwitch(["OverloadUtility"], onCmd = json.dumps(self.getSetValueDict("PEb", extern = True)), offCmd = json.dumps(self.getSetValueDict("PDb", extern = True)))
        self.initialMqttSend = True
        self.queryIndex = 0
        self.queries = [
            "QMUCHGCR",      # should be the first entry!
            "QPI",
            "QID",
            "QVFW",
            "QVFW2",
            #"QVFW3",        # seems to be empty
            #"QVFW4",        # seems to be empty
            "QPIRI",
            "QFLAG",
            #"QPIGS",        # read every 20ms by default
            #"QPIGS2",       # seems to be empty
            #"QPGSn",        # do we need this?
            #"QP2GSn",       # do we need this?
            #"QMOD",         # read every 20ms by default
            "QPIWS",
            "QDI",
            "QMCHGCR",
            #"QMSCHGCR",     # seems to be empty
            "QBOOT",
            "QOPM",
            #"QCST",         # seems to be empty
            #"QCVT"          # seems to be empty
        ]

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

        if self.timer(name = "queryTimer", timeout = effekta_Query_Cycle, autoReset = True, firstTimeTrue = True):
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QPIGS"), globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMOD"),  globalPublish = False, enableEcho = False)

            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict(self.queries[self.queryIndex]),   globalPublish = False, enableEcho = False)
            self.queryIndex += 1
            if self.queryIndex >= len(self.queries):
                self.queryIndex = 0

        self.sendeGlobalMqtt = False

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

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
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"]["query"], globalPublish = True, enableEcho = False)
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMUCHGCR" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        if not self.valideChargeValues:
                            # If valideChargeValues is empty we fill it with effekta answers
                            self.valideChargeValues = newMqttMessageDict["content"]["query"]["response"].split()
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMOD" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        if self.EffektaData["EffektaWerte"]["ActualMode"] != newMqttMessageDict["content"]["query"]["response"]:
                            self.sendeGlobalMqtt = True
                            self.EffektaData["EffektaWerte"]["ActualMode"] = newMqttMessageDict["content"]["query"]["response"]
                            if self.EffektaData["EffektaWerte"]["ActualMode"] in self.fullTextMode:
                                self.EffektaData["EffektaWerte"]["ActualModeText"] = self.fullTextMode[self.EffektaData["EffektaWerte"]["ActualMode"]]
                            else:
                                self.EffektaData["EffektaWerte"]["ActualModeText"] = "unknown mode"
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QPIGS" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        (Netzspannung, Netzfrequenz, AcOutSpannung, AcOutFrequenz, AcOutPowerVA, AcOutPower, AcOutLoadProz, BusVoltage, BattSpannung, BattCharge, BattCapacity, InverterTemp, PvCurrent, PvVoltage, BattVoltageSCC, BattDischarge, DeviceStatus1, BattOffset, EeVersion, PvPower, DeviceStatus2) = newMqttMessageDict["content"]["query"]["response"].split()
                        self.EffektaData["EffektaWerte"]["AcOutSpannung"] = float(AcOutSpannung)

                        # If first data arrived, and software just start up we want to send. Powerplant checks this.
                        if self.initialMqttSend:
                            self.initialMqttSend = False
                            self.sendeGlobalMqtt = True

                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["Netzspannung"], int(float(Netzspannung)), -1, 10000, percent = 3, dynamic = True)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["AcOutPower"], int(AcOutPower), -1, 10000, percent = 10, dynamic = True)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["PvPower"], int(PvPower), -1, 10000, percent = 10, dynamic = True)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["BattCharge"], int(BattCharge), -1, 10000, percent = 10, dynamic = True)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["BattDischarge"], int(BattDischarge), -1, 10000, percent = 10, dynamic = True)
                        self.sendeGlobalMqtt |= (self.EffektaData["EffektaWerte"]["DeviceStatus2"] != DeviceStatus2)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["BattSpannung"], float(BattSpannung), -1, 100, percent = 0.5, dynamic = True)
                        self.sendeGlobalMqtt |= Supporter.deltaOutsideRange(self.EffektaData["EffektaWerte"]["BattCapacity"], int(BattCapacity), -1, 101, percent = 1, dynamic = True)
                        if self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["Netzspannung"]  = int(float(Netzspannung))
                            self.EffektaData["EffektaWerte"]["AcOutPower"]    = int(AcOutPower)
                            self.EffektaData["EffektaWerte"]["PvPower"]       = int(PvPower)
                            self.EffektaData["EffektaWerte"]["BattCharge"]    = int(BattCharge)
                            self.EffektaData["EffektaWerte"]["BattDischarge"] = int(BattDischarge)
                            self.EffektaData["EffektaWerte"]["DeviceStatus2"] = DeviceStatus2
                            self.EffektaData["EffektaWerte"]["BattSpannung"]  = float(BattSpannung)
                            self.EffektaData["EffektaWerte"]["BattCapacity"]  = int(BattCapacity)

                        self.tempDailyProduction = self.tempDailyProduction + (int(PvPower) * effekta_Query_Cycle / 60 / 60 / 1000)
                        self.EffektaData["EffektaWerte"]["DailyProduction"] = round(self.tempDailyProduction, 2)
                    else:
                        self.logger.logger.logger.info(self, f"unhandled Effekta message: {newMqttMessageDict['content']}")


        now = datetime.datetime.now()
        if now.hour == 23:
            if self.EffektaData["EffektaWerte"]["DailyProduction"] > 0.0:
                self.EffektaData["EffektaWerte"]["CompleteProduction"] = self.EffektaData["EffektaWerte"]["CompleteProduction"] + round(self.EffektaData["EffektaWerte"]["DailyProduction"])
                self.EffektaData["EffektaWerte"]["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
                self.sendeGlobalMqtt = True

        if self.sendeGlobalMqtt:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = True,  enableEcho = False)
            self.sendeGlobalMqtt = False
        else:
            pass
            # @todo send aktual values here
            #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(1)