from Base.InterfaceBase import InterfaceBase
import time
import pylontech       # pip install pylontech
#from pylontech import PylontechStack
from Interface.Uart.Pylontech.pylontech_stack import PylontechStack
from GridLoad.SocMeter import SocMeter
from BMS.BasicBms import BasicBms

class Pylontech485Interface(InterfaceBase):
    '''
    classdocs
    '''
    MAX_PACK_VOLTAGE = 53.5

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.removeMqttRxQueue()
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Tmin": -40.0, "Tmax": -40.0, "Current":0.0, "CurrentList":[], "VoltageList":[], "PackVoltageList":[], "ChargeDischargeManagement":{}, "Prozent":SocMeter.InitAkkuProz, "Power":0.0,"toggleIfMsgSeen":False, "BmsLadeFreigabe":True, "BmsEntladeFreigabe":False}
        self.ChDchManagementList = ["StatusFullChargeRequired", "ChargeVoltage", "DischargeVoltage", "ChargeCurrent", "DischargeCurrent"]
        self.TranslateDict = {"StatusFullChargeRequired":"FullChargeRequired", "ChargeVoltage":"BoostVoltage"}

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "battCount", "VminCellWarn", "VmaxCellWarn", "VminWarnTimer", "VmaxWarnTimer"])
        self.tagsIncluded(["baudrate"], optional = True, default = 115200)
        self.tagsIncluded(["NumLogfiles"], optional = True, default = 20)
        self.printError = True
        self.LogIndex = 0
        self.printRawData = False
        tries = 0
        while tries < self.MAX_INIT_TRIES:
            try:
                self.p = PylontechStack(self.configuration["interface"], baud=self.configuration["baudrate"], manualBattcountLimit=self.configuration["battCount"])
                break
            except:
                time.sleep(10)
                self.logger.info(self, f"Device --{self.name}-- {tries + 1} from {self.MAX_INIT_TRIES} inits failed.")
            tries += 1
        if tries >= self.MAX_INIT_TRIES:
            raise Exception(f'{self.name} connection could not established! Check interface, baudrate, battCount!')

        #print(p.update())
        #{'SerialNumbers': ['K221027C30801415'], 'Calculated': {'TotalCapacity_Ah': 50.0, 'RemainCapacity_Ah': 25.0, 'Remain_Percent': 50.0, 'Power_kW': 0.0, 'ChargePower_kW': 0, 'DischargePower_kW': -0.0}, 'AnaloglList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 110, 'PAYLOAD': b'00020F0CDD0CDB0CDC0CDC0CDD0CDD0CDD0CDC0CDD0CDC0CDD0CDD0CDD0CDB0CDD050B680B460B450B440B580000C0EB61A802C3500000', 'InfoFlag': 0, 'CommandValue': 2, 'CellCount': 15, 'CellVoltages': [3.293, 3.291, 3.292, 3.292, 3.293, 3.293, 3.293, 3.292, 3.293, 3.292, 3.293, 3.293, 3.293, 3.291, 3.293], 'TemperatureCount': 5, 'Temperatures': [18.9, 15.5, 15.4, 15.3, 17.3], 'Current': 0.0, 'Voltage': 49.387, 'RemainCapacity': 25.0, 'CapDetect': '<=65Ah', 'ModuleTotalCapacity': 50.0, 'CycleNumber': 0}], 'ChargeDischargeManagementList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 20, 'PAYLOAD': b'02D002AFC800FAFF06C0', 'CommandValue': 2, 'ChargeVoltage': 53.25, 'DischargeVoltage': 45.0, 'ChargeCurrent': 25.0, 'DischargeCurrent': -25.0, 'StatusChargeEnable': True, 'StatusDischargeEnable': True, 'StatusChargeImmediately1': False, 'StatusChargeImmediately2': False, 'StatusFullChargeRequired': False}], 'AlarmInfoList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 66, 'PAYLOAD': b'00020F000000000000000000000000000000050000000000000000000E00000000', 'InfoFlag': 0, 'CommandValue': 2, 'CellCount': 15, 'CellAlarm': ['Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok'], 'TemperatureCount': 5, 'TemperatureAlarm': ['Ok', 'Ok', 'Ok', 'Ok', 'Ok'], 'ChargeCurentAlarm': 'Ok', 'ModuleVoltageAlarm': 'Ok', 'DischargeCurrentAlarm': 'Ok', 'Status1': 0, 'Status2': 14, 'Status3': 0, 'Status4': 0, 'Status5': 0}]}



    def threadMethod(self):
        try:
            data = self.p.update()
            if self.timerExists("timeoutPylontechRead"):
                self.timer(name = "timeoutPylontechRead",remove = True)
            self.BmsWerte["VoltageList"] = []
            valueList = []
            self.BmsWerte["PackVoltageList"] = []
            self.BmsWerte["CurrentList"] = []
            self.BmsWerte["Current"] = 0.0
            for module in data["AnaloglList"]:
                self.BmsWerte["VoltageList"] += module["CellVoltages"]
                valueList += module["Temperatures"]
                self.BmsWerte["PackVoltageList"].append(module["Voltage"])
                self.BmsWerte["Current"] += module["Current"]
                self.BmsWerte["CurrentList"].append(module["Current"])

            self.BmsWerte["Vmin"] = min(self.BmsWerte["VoltageList"])
            self.BmsWerte["Vmax"] = max(self.BmsWerte["VoltageList"])
            self.BmsWerte["Tmin"] = min(valueList)
            self.BmsWerte["Tmax"] = max(valueList)

            # Extract BmsEntladeFreigabe and BmsLadeFreigabe from CellAlarm  
            self.BmsWerte["BmsEntladeFreigabe"] = True
            self.BmsWerte["BmsLadeFreigabe"] = True
            for module in data["AlarmInfoList"]:
                #if not data["ChargeDischargeManagementList"]["StatusDischargeEnable"]:
                if module["ModuleVoltageAlarm"] != "Ok":
                    self.printRawData = True
                    if self.BmsWerte["Vmin"] < 3.0:
                        self.BmsWerte["BmsEntladeFreigabe"] = False
                        self.logger.error(self, f'Pylontec ModuleVoltageAlarm detected')
                    if self.BmsWerte["Vmax"] > 3.5:
                        self.BmsWerte["BmsLadeFreigabe"] = False
                        self.logger.error(self, f'Pylontec ModuleVoltageAlarm detected')
                for cellAlarm in module["CellAlarm"]:
                    if cellAlarm != "Ok":
                        self.printRawData = True
                        if self.BmsWerte["Vmin"] < 3.0:
                            self.BmsWerte["BmsEntladeFreigabe"] = False
                        if self.BmsWerte["Vmax"] > 3.5:
                            self.BmsWerte["BmsLadeFreigabe"] = False
                        self.logger.error(self, f'Pylontec CellAlarm in str: str(module["CellAlarm"])')

            # Check cell voltages with given parameters to create a warning. We need this to prevent a low or high voltage disconnect.
            if self.BmsWerte["Vmin"] <= self.configuration["VminCellWarn"]:
                if self.timer(name = "VminTimer", timeout = self.configuration["VminWarnTimer"], autoReset = False):
                    self.BmsWerte["BmsEntladeFreigabe"] = False
                    if self.printError:
                        self.printError = False
                        self.logger.error(self, f'VminCellWarn from {self.name} has triggered, we stop discharging.')
                    self.printRawData = True
            else:
                if self.timerExists("VminTimer"):
                    self.printError = True
                    self.timer(name = "VminTimer", remove = True)

            if self.BmsWerte["Vmax"] >= self.configuration["VmaxCellWarn"]:
                if self.timer(name = "VmaxTimer", timeout = self.configuration["VmaxWarnTimer"], autoReset = False):
                    self.BmsWerte["BmsLadeFreigabe"] = False
                    if self.printError:
                        self.printError = False
                        self.logger.error(self, f'VmaxCellWarn from {self.name} has triggered, we stop charging.')
                    self.printRawData = True
            else:
                if self.timerExists("VmaxTimer"):
                    self.printError = True
                    self.timer(name = "VmaxTimer",remove = True)

            if max(self.BmsWerte["PackVoltageList"]) >= self.MAX_PACK_VOLTAGE:
                if self.timer(name = "Write error", firstTimeTrue = True, timeout = 120):
                    self.logger.error(self, f'MaxPackVoltage from {self.name} has triggered, we stop charging.')
                    self.logger.error(self, f'Pack Voltages: {str(self.BmsWerte["PackVoltageList"])}')
                self.printRawData = True
                self.BmsWerte["BmsLadeFreigabe"] = False


            if self.printRawData:
                if self.timer(name = "WriteErrorLog", firstTimeTrue = True, timeout = 60*60*2):
                    self.logger.error(self, f'Error from Pylontec detected. Pylontec rawData:')
                    self.logger.error(self, f'str(data)')
                    self.LogIndex += 1
                    self.logger.writeLogBufferToDisk(f"logfiles/{self.name}_{str(self.LogIndex)}_pylontec_error.log")

            if self.LogIndex >= self.configuration["NumLogfiles"]:
                self.LogIndex = 0

            # filter some values from ChargeDischargeManagementList and merge them
            tempList =[]
            for moduleChDchList in data["ChargeDischargeManagementList"]:
                tempDict = {}
                for key in self.ChDchManagementList:
                    if key in self.TranslateDict:
                        tempDict[self.TranslateDict[key]] = moduleChDchList[key]
                    else:
                        tempDict[key] = moduleChDchList[key]
                tempDict["BoostVoltage"] = round(tempDict["BoostVoltage"] * 0.995, 2)     # coose a little lower value to prevent blowing fuses at 54.0V
                tempList.append(tempDict)


            '''
                tempList with two pylontechs: 
                  [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 20, 'PAYLOAD': b'02D002AFC800FAFF06C0', 
                 'CommandValue': 2, 'ChargeVoltage': 53.25, 'DischargeVoltage': 45.0, 'ChargeCurrent': 25.0, 'DischargeCurrent': 
                 -25.0, 'StatusChargeEnable': True, 'StatusDischargeEnable': True, 'StatusChargeImmediately1': False, 
                 'StatusChargeImmediately2': False, 'StatusFullChargeRequired': False}, {'VER': 32, 'ADR': 3, 'ID': 70, 'RTN': 0, 
                 'LENGTH': 20, 'PAYLOAD': b'03D002AFC80000FF06C0', 'CommandValue': 3, 'ChargeVoltage': 53.25, 
                 'DischargeVoltage': 45.0, 'ChargeCurrent': 0.0, 'DischargeCurrent': -25.0, 'StatusChargeEnable': True, 
                 'StatusDischargeEnable': True, 'StatusChargeImmediately1': False, 'StatusChargeImmediately2': False, 
                 'StatusFullChargeRequired': False}]
            '''

            if len(tempList) >= 2:
                self.BmsWerte["ChargeDischargeManagement"] = BasicBms.dictMerger(tempList)
            else:
                self.BmsWerte["ChargeDischargeManagement"] = tempList[0]

            self.BmsWerte["Prozent"] = data["Calculated"]["Remain_Percent"]
            self.BmsWerte["Ah"] = data["Calculated"]["RemainCapacity_Ah"]
            self.BmsWerte["Power"] = data["Calculated"]["Power_W"]
    
            self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
    
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)
        except Exception as exception:
            self.logger.error(self, f"Error reading {self.name} interface.")
            self.logger.error(self, f"{exception}")
            if self.timer(name = "timeoutPylontechRead", timeout = 60):
                raise Exception(f'{self.name} connection is broken since 60s!')

    def threadBreak(self):
        time.sleep(1.5)