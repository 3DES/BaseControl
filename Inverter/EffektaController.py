import time
import datetime
import json
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter
from Logger.Logger import Logger
from BMS.BasicBms import BasicBms

class EffektaController(ThreadObject):
    '''
    classdocs

    A parameter rerquest can be triggered with following command. Where Ost ist the threadName.
    HomeAccu/Ost/in/queryExtern QPIGS
    HomeAccu/Ost/out {"cmd": "QPIGS", "response": "231.1 49.9 000.0 00.0 0000 0000 000 054 49.10 000 059 0020 0000 062.4 49.22 00000 00000110 00 00 00044 000", "extern": true}

    '''
    VerbraucherNetz = "POP00"       # load prio 00=Netz, 02=Batt, 01=PV und Batt, wenn PV verfügbar ansonsten Netz
    VerbraucherAkku = "POP02"       # load prio 00=Netz, 02=Batt, 01=PV und Batt, wenn PV verfügbar ansonsten Netz
    BattLeer = "PSDV43.0"
    BattWiederEntladen = "PBDV48.0"
    chargePrioNetzPV = "PCP02"              # charge prio 02=Netz und pv, 03=pv
    chargePrioPV = "PCP03"                  # charge prio 02=Netz und pv, 03=pv
    chargeBoostVoltageCmd = "PCVV"
    chargeFloatVoltageCmd = "PBFT"
    chargeBoostTimeCmd = "PCVT"

    fullTextMode = {
        "P" : "Power on mode",
        "S" : "Standby mode",
        "L" : "Grid mode",
        "B" : "Battery mode",
        "F" : "Fault mode",
        "H" : "Power saving mode"
    }
    MQTT_TIMEOUT = 60
    ValideChargeValues = []
    BMS_TIMEOUT = 300
    
    FAST_CHARGE_ON = "fastChargeOn"
    SLOW_CHARGE_ON = "slowChargeOn"
    GRID_CHARGER_OFF = "gridChargerOff"
    SWITCH_TO_BATTERY = "switchToBattery"
    SWITCH_TO_GRID = "switchToGrid"
    WORK_DATA_KEYS = ["ActualMode", "AcOutSpannung", "Netzspannung", "DeviceStatus2"]        # necessary to call funktion getCombinedEffektaData(), so caller can check if all keys are included
    CHARGE_DISCHARGE_PARAMETERS = ["FloatVoltage", "BoostVoltage", "BoostTime"]


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)

    @classmethod
    def prepareBoostChargeTimeCmd(cls, minutes:int):
        '''
        returns the given minutes rounded in 5 min steps with command string
        '''
        step = 5
        minutes = int(round(minutes/step, 0)) * step
        return f"{cls.chargeBoostTimeCmd}{minutes:03}"

    @classmethod
    def prepareUtilityChargeCmd(cls, inverterIndex:int, current:int):
        if inverterIndex > 9:
            raise Exception(f"{self.name}: inverterIndex must be < 9!")
        if current >= 100:
            return f"MNCHGC{inverterIndex}{current:03}"
        else:
            return f"MUCHGC{inverterIndex}{current:02}"

    @classmethod
    def getSetValueKeys(cls, cmd, value = "", extern = False):
        return {"cmd":cmd, "value":value, "response": "", "success": False, "extern":extern}

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
    def getCmdForceChargerToFloat(cls):
        parList = []
        # wir verstellen die Ladespannung (float und boost!!)
        # parList.append(cls.getSetValueKeys(cls.SetChargeToFloatmode))
        return {"setValue":parList}

    @classmethod
    def getCmdEnableChargerBoostMode(cls):
        parList = []
        # wir verstellen die Ladespannung (float und boost!!)
        # parList.append(cls.getSetValueKeys(cls.BattWiederEntladen))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchUtilityChargeOn(cls, inverterIndex:int = 0):
        # We set the lowest value of valideChargeValues (normally 2A charge current)
        parList = []
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys(cls.prepareUtilityChargeCmd(inverterIndex, int(cls.ValideChargeValues[0]))))
        return {"setValue":parList}

    @classmethod
    def getCmdSwitchUtilityFastChargeOn(cls, inverterIndex:int = 0):
        # We set the middle value of valideChargeValues (normally 30A charge current)
        parList = []
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys(cls.prepareUtilityChargeCmd(inverterIndex, int(cls.ValideChargeValues[round(len(cls.ValideChargeValues) / 2) - 1]))))
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
    def getCmdSwitchToUtilityChargingWithUvDetection(cls, inverterIndex:int = 0):
        parList = []
        parList.append(cls.getSetValueKeys(cls.VerbraucherNetz))
        parList.append(cls.getSetValueKeys("PBDV52.0"))
        parList.append(cls.getSetValueKeys("PSDV48.0"))
        parList.append(cls.getSetValueKeys(cls.prepareUtilityChargeCmd(inverterIndex, int(cls.ValideChargeValues[0]))))
        parList.append(cls.getSetValueKeys(cls.chargePrioNetzPV))
        return {"setValue":parList}

    @classmethod
    def getCombinedEffektaData(cls, EffektaData):
        """
        returns given Effekta data with logical link
        given data is a dict with one or more Effektas {"effekta_A":{Data}, "effekta_B":{Data}}
        """
        globalEffektaData = {"BatteryModeAnd" : True, "FloatingModeOr" : False, "OutputVoltageHighOr" : False, "InputVoltageAnd" : True, "OutputVoltageHighAnd" : True, "OutputVoltageLowAnd" : True, "ErrorPresentOr" : False}
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
                if EffektaData[name]["ActualMode"] != "B":
                    globalEffektaData["BatteryModeAnd"] = False
        except Exception as ex:
            cls.logger.error(cls, f"Wir konnten CombinedEffektaData nicht bilden. Exception:{ex}, EffektaData:{EffektaData}, Aktueller key:{currentlyHandledKey}, floatmode:{floatmode}")
        return globalEffektaData

    def sendProjectFileChargeParameters(self):
        self.mqttPublish(self.interfaceInTopics[0], self.getSetValueDict(cmd = self.chargeBoostVoltageCmd, value = str(round(self.configuration["boostVoltage"], 1)), extern = False), globalPublish = False, enableEcho = False)
        self.mqttPublish(self.interfaceInTopics[0], self.getSetValueDict(cmd = self.chargeFloatVoltageCmd, value = str(round(self.configuration["floatVoltage"], 1)), extern = False), globalPublish = False, enableEcho = False)
        self.mqttPublish(self.interfaceInTopics[0], self.getSetValueDict(cmd = self.prepareBoostChargeTimeCmd(self.configuration["boostTime"]), extern = False), globalPublish = False, enableEcho = False)

    def copyAndConvertChargeParameters(self):
        # copy and convert names from jsonFileParamters to projectJsonChargeParameters initial
        try:
            self.projectJsonChargeParameters
        except:
            self.projectJsonChargeParameters = {}
            for parameter in self.CHARGE_DISCHARGE_PARAMETERS:
                projectJsonParameterName = parameter[0].lower() + parameter[1:]
                if projectJsonParameterName in self.configuration:
                    self.projectJsonChargeParameters[parameter] = self.configuration[projectJsonParameterName]

    def threadInitMethod(self):
        self.tagsIncluded(["bmsName"])
        # "floatVoltage","boostVoltage", "boostTime" we check later if bms data is arrived
        self.tagsIncluded(["inverterIndex"], optional = True, default = 0)
        self.copyAndConvertChargeParameters()
        self.EffektaData = {"BmsWerte":{"BmsEntladeFreigabe":True, "BmsLadeFreigabe":True}, "EffektaWerte": {"Netzspannung": 0, "AcOutSpannung": 0, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "", "ActualModeText": "", "DailyProduction": 0.0, "CompleteProduction": 0, "BattCapacity": 0, "DeviceStatus2": "", "BattSpannung": 0.0}}
        self.tempDailyProduction = 0.0
        self.sendChDchStatesInitial = True
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        self.OldMqttDataReceived = False
        self.sendInitialParamters = True
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()) + "/#", globalSubscription = True)
        #self.mqttSubscribeTopic(self.createInTopic(self.getClassTopic()) + "/#", globalSubscription = True)
        self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(self.configuration["bmsName"])), globalSubscription = False)

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self.EffektaData["EffektaWerte"])
        self.homeAutomation.mqttDiscoverySwitch(["OverloadUtility"], onCmd = json.dumps(self.getSetValueDict("PEb", extern = True)), offCmd = json.dumps(self.getSetValueDict("PDb", extern = True)))
        self.initialMqttSend = True
        self.queryIndex = 0
        self.queries = [
            "QMUCHGCR",      # has to be the first entry, otherwise some "if" statements will fail!
            # "QPI",
            # "QID",
            # "QVFW",
            # "QVFW2",
            # #"QVFW3",        # seems to be empty
            # #"QVFW4",        # seems to be empty
            # "QPIRI",
            # "QFLAG",
            # #"QPIGS",        # read every 20ms by default
            # #"QPIGS2",       # seems to be empty
            # #"QPGSn",        # do we need this?
            # #"QP2GSn",       # do we need this?
            # #"QMOD",         # read every 20ms by default
            # "QPIWS",
            # "QDI",
            # "QMCHGCR",
            # #"QMSCHGCR",     # seems to be empty
            # "QBOOT",
            # "QOPM",
            # #"QCST",         # seems to be empty
            # #"QCVT"          # seems to be empty
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
        if self.timer(name="bmsTimeout", timeout=self.BMS_TIMEOUT):
            raise Exception(f'{self.name} received no data from bms {self.configuration["bmsName"]} for more than {self.BMS_TIMEOUT}s!')

        effekta_Query_Cycle = 20

        if self.timer(name = "queryTimer", timeout = effekta_Query_Cycle, autoReset = True, firstTimeTrue = True):
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict(self.queries[self.queryIndex]),   globalPublish = False, enableEcho = False)
            self.queryIndex += 1
            if self.queryIndex >= len(self.queries):
                self.queryIndex = 0
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QPIGS"), globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], self.getQueryDict("QMOD"),  globalPublish = False, enableEcho = False)

        self.sendeGlobalMqtt = False

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            # First we check if the msg is from our Interface
            if newMqttMessageDict["topic"] in self.interfaceOutTopics:
                # The msg is from our interface
                if "setValue" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["setValue"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"]["setValue"]["success"], globalPublish = True, enableEcho = False)
                    elif not newMqttMessageDict["content"]["setValue"]["success"]:
                        self.logger.error(self, f'setValue to inverter {self.name} was not successfull. Cmd was: {newMqttMessageDict["content"]}')
                        # With internal parameters we don't allow errors. Because for example charging parameters are very sensible.
                        raise Exception(f"Could not send value to inverter. Check Connection!")
                elif "query" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["query"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"]["query"], globalPublish = True, enableEcho = False)
                    elif len(newMqttMessageDict["content"]["query"]["response"]) == 0:
                        self.logger.error(self, f'Query to inverter {self.name} was not successfull. No data received or missmatched CRC! Cmd was: {newMqttMessageDict["content"]}')
                    elif newMqttMessageDict["content"]["query"]["response"] == "NAK":
                        self.logger.error(self, f'Query to inverter {self.name} was rejected. Cmd was: {newMqttMessageDict["content"]}')
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMUCHGCR":
                        EffektaController.ValideChargeValues = sorted(newMqttMessageDict["content"]["query"]["response"].split())
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMOD":
                        if self.EffektaData["EffektaWerte"]["ActualMode"] != newMqttMessageDict["content"]["query"]["response"]:
                            self.sendeGlobalMqtt = True
                            self.EffektaData["EffektaWerte"]["ActualMode"] = newMqttMessageDict["content"]["query"]["response"]
                            if self.EffektaData["EffektaWerte"]["ActualMode"] in self.fullTextMode:
                                self.EffektaData["EffektaWerte"]["ActualModeText"] = self.fullTextMode[self.EffektaData["EffektaWerte"]["ActualMode"]]
                            else:
                                self.EffektaData["EffektaWerte"]["ActualModeText"] = "unknown mode"
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QPIGS":
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
                        self.logger.info(self, f"unhandled Effekta message: {newMqttMessageDict['content']}")
            elif self.createOutTopic(self.createProjectTopic(self.configuration["bmsName"])) == newMqttMessageDict["topic"]:
                if "BmsEntladeFreigabe" in newMqttMessageDict["content"]:
                    if self.timerExists("bmsTimeout"):
                        self.timer(name="bmsTimeout", timeout=self.BMS_TIMEOUT, remove=True)
                    if (self.EffektaData["BmsWerte"]["BmsEntladeFreigabe"] == True) and (newMqttMessageDict["content"]["BmsEntladeFreigabe"] == False):
                        self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchToUtilityChargingWithUvDetection(inverterIndex = self.configuration["inverterIndex"]), globalPublish = False, enableEcho = False)
                    #if (self.EffektaData["BmsWerte"]["BmsLadeFreigabe"] != newMqttMessageDict["content"]["BmsLadeFreigabe"]) or self.sendChDchStatesInitial:
                    #    if newMqttMessageDict["content"]["BmsLadeFreigabe"] == True:
                    #        self.mqttPublish(self.interfaceInTopics[0], self.getCmdEnableChargerBoostMode(), globalPublish = False, enableEcho = False)
                    #    else:
                    #        self.mqttPublish(self.interfaceInTopics[0], self.getCmdForceChargerToFloat(), globalPublish = False, enableEcho = False)
                    self.sendChDchStatesInitial = False
                    self.EffektaData["BmsWerte"].update(newMqttMessageDict["content"])
                    # if BmsEntladeFreigabe is in bms data then it is a msg with all ChDch infos 
                    if "ChargeDischargeManagement" in newMqttMessageDict["content"]:
                        # built mergelist and merge the data
                        mergeParameters = []
                        mergeParameters.append(self.projectJsonChargeParameters)
                        mergeParameters.append(newMqttMessageDict["content"]["ChargeDischargeManagement"])
                        newParameters = BasicBms.dictMerger(mergeParameters, {"BoostTime" : max}, verbose = False)  # give missing mergeMethod and noverbose because dicts dont containing the same keys
                        initDict = False
                        # init "ChargeDischargeManagement" if it is not present yet
                        if "ChDchParameters" not in self.EffektaData:
                            initDict = True
                            self.EffektaData["ChDchParameters"] = {}
                        # delete not needed keys for better comparison and init "ChargeDischargeManagement" if needed
                        for key in list(newParameters):
                            if key not in self.CHARGE_DISCHARGE_PARAMETERS:
                                del newParameters[key]
                            elif initDict:
                                self.EffektaData["ChDchParameters"][key] = None
                        # check newParameters once at startup to generate a nice error msg
                        if initDict:
                            for key in self.CHARGE_DISCHARGE_PARAMETERS:
                                if key not in newParameters:
                                    raise Exception(f'Not all charge parameters are present after merge! Missing: {key}')
                        if newParameters["FloatVoltage"] > newParameters["BoostVoltage"]:
                            raise Exception(f'FLoatVoltage is higher than BoostVoltage! FLoat: {newParameters["FloatVoltage"]}, Boost: {newParameters["BoostVoltage"]}. Check project.json or your battery.')
                        # handle each parameter separate to reduce eeprom write cycles
                        if self.EffektaData["ChDchParameters"]["BoostVoltage"] != newParameters["BoostVoltage"]:
                            cmd = self.getSetValueDict(cmd = self.chargeBoostVoltageCmd, value = str(round(newParameters["BoostVoltage"], 1)), extern = False)
                            self.logger.info(self, f"Set parameter BoostVoltage with cmd: {cmd}")
                            self.mqttPublish(self.interfaceInTopics[0], cmd, globalPublish = False, enableEcho = False)
                        if self.EffektaData["ChDchParameters"]["FloatVoltage"] != newParameters["FloatVoltage"]:
                            cmd = self.getSetValueDict(cmd = self.chargeFloatVoltageCmd, value = str(round(newParameters["FloatVoltage"], 1)), extern = False)
                            self.logger.info(self, f"Set parameter FloatVoltage with cmd: {cmd}")
                            self.mqttPublish(self.interfaceInTopics[0], cmd, globalPublish = False, enableEcho = False)
                        if self.EffektaData["ChDchParameters"]["BoostTime"] != newParameters["BoostTime"]:
                            cmd = self.getSetValueDict(cmd = self.prepareBoostChargeTimeCmd(newParameters["BoostTime"]), extern = False)
                            self.logger.info(self, f"Set parameter BoostTime with cmd: {cmd}")
                            self.mqttPublish(self.interfaceInTopics[0], cmd, globalPublish = False, enableEcho = False)
                        self.EffektaData["ChDchParameters"].update(newParameters)
                        self.sendInitialParamters = False
                    elif self.sendInitialParamters:
                        self.tagsIncluded(["floatVoltage","boostVoltage", "boostTime"])
                        self.sendProjectFileChargeParameters()
                        self.sendInitialParamters = False
            else:
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
                elif self.SWITCH_TO_GRID == newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchToUtility(), globalPublish = False, enableEcho = False)
                elif self.SWITCH_TO_BATTERY == newMqttMessageDict["content"] and (self.EffektaData["BmsWerte"]["BmsEntladeFreigabe"] == True):
                    self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchToBattery(), globalPublish = False, enableEcho = False)
                elif self.GRID_CHARGER_OFF == newMqttMessageDict["content"] and (self.EffektaData["BmsWerte"]["BmsEntladeFreigabe"] == True):
                    self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchUtilityChargeOff(), globalPublish = False, enableEcho = False)
                elif self.SLOW_CHARGE_ON == newMqttMessageDict["content"] and (self.EffektaData["BmsWerte"]["BmsLadeFreigabe"] == True):
                    self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchUtilityChargeOn(inverterIndex = self.configuration["inverterIndex"]), globalPublish = False, enableEcho = False)
                elif self.FAST_CHARGE_ON == newMqttMessageDict["content"] and (self.EffektaData["BmsWerte"]["BmsLadeFreigabe"] == True):
                    self.mqttPublish(self.interfaceInTopics[0], self.getCmdSwitchUtilityFastChargeOn(inverterIndex = self.configuration["inverterIndex"]), globalPublish = False, enableEcho = False)
                elif "CompleteProduction" in newMqttMessageDict["content"]:
                    # if we receive our old data we overwrite our initial value
                    self.EffektaData["EffektaWerte"]["CompleteProduction"] = newMqttMessageDict["content"]["CompleteProduction"]
                    self.EffektaData["EffektaWerte"]["DailyProduction"] = newMqttMessageDict["content"]["DailyProduction"]
                    self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
                    self.OldMqttDataReceived = True

        now = datetime.datetime.now()
        if now.hour == 23:
            if self.EffektaData["EffektaWerte"]["DailyProduction"] > 0.0:
                self.EffektaData["EffektaWerte"]["CompleteProduction"] = self.EffektaData["EffektaWerte"]["CompleteProduction"] + round(self.EffektaData["EffektaWerte"]["DailyProduction"])
                self.EffektaData["EffektaWerte"]["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
                self.sendeGlobalMqtt = True

        if not self.OldMqttDataReceived:
            if self.timer("mqttTimeout", self.MQTT_TIMEOUT, removeOnTimeout = True):
                self.OldMqttDataReceived = True

        if self.sendeGlobalMqtt and self.OldMqttDataReceived:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = True,  enableEcho = False)
            self.sendeGlobalMqtt = False
        else:
            pass
            # @todo send aktual values here
            #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData["EffektaWerte"], globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(1)