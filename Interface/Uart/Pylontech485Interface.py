from Base.InterfaceBase import InterfaceBase
import time
import pylontech       # pip install pylontech
#from pylontech import PylontechStack
from Interface.Uart.Pylontech.pylontech_stack import PylontechStack
from GridLoad.SocMeter import SocMeter

class Pylontech485Interface(InterfaceBase):
    '''
    classdocs
    '''
    
    maxInitTries = 10

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Tmin": -40.0, "Tmax": -40.0, "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "Power":0.0,"toggleIfMsgSeen":False, "FullChargeRequired":False, "BmsLadeFreigabe":True, "BmsEntladeFreigabe":False}

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "battCount"])
        self.tagsIncluded(["baudrate"], optional = True, default = 115200)
        self.tries = 0
        while self.tries <= self.maxInitTries:
            self.tries += 1
            try:
                self.p = PylontechStack(self.configuration["interface"], baud=self.configuration["baudrate"], manualBattcountLimit=self.configuration["battCount"])
                break
            except:
                time.sleep(10)
                self.logger.info(self, f"Device --{self.name}-- {self.tries} from {self.maxInitTries} inits failed.")
                if self.tries >= self.maxInitTries:
                    raise Exception(f'{self.name} connection could not established! Check interface, baudrate, battCount!')

        #print(p.update())
        #{'SerialNumbers': ['K221027C30801415'], 'Calculated': {'TotalCapacity_Ah': 50.0, 'RemainCapacity_Ah': 25.0, 'Remain_Percent': 50.0, 'Power_kW': 0.0, 'ChargePower_kW': 0, 'DischargePower_kW': -0.0}, 'AnaloglList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 110, 'PAYLOAD': b'00020F0CDD0CDB0CDC0CDC0CDD0CDD0CDD0CDC0CDD0CDC0CDD0CDD0CDD0CDB0CDD050B680B460B450B440B580000C0EB61A802C3500000', 'InfoFlag': 0, 'CommandValue': 2, 'CellCount': 15, 'CellVoltages': [3.293, 3.291, 3.292, 3.292, 3.293, 3.293, 3.293, 3.292, 3.293, 3.292, 3.293, 3.293, 3.293, 3.291, 3.293], 'TemperatureCount': 5, 'Temperatures': [18.9, 15.5, 15.4, 15.3, 17.3], 'Current': 0.0, 'Voltage': 49.387, 'RemainCapacity': 25.0, 'CapDetect': '<=65Ah', 'ModuleTotalCapacity': 50.0, 'CycleNumber': 0}], 'ChargeDischargeManagementList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 20, 'PAYLOAD': b'02D002AFC800FAFF06C0', 'CommandValue': 2, 'ChargeVoltage': 53.25, 'DischargeVoltage': 45.0, 'ChargeCurrent': 25.0, 'DischargeCurrent': -25.0, 'StatusChargeEnable': True, 'StatusDischargeEnable': True, 'StatusChargeImmediately1': False, 'StatusChargeImmediately2': False, 'StatusFullChargeRequired': False}], 'AlarmInfoList': [{'VER': 32, 'ADR': 2, 'ID': 70, 'RTN': 0, 'LENGTH': 66, 'PAYLOAD': b'00020F000000000000000000000000000000050000000000000000000E00000000', 'InfoFlag': 0, 'CommandValue': 2, 'CellCount': 15, 'CellAlarm': ['Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok', 'Ok'], 'TemperatureCount': 5, 'TemperatureAlarm': ['Ok', 'Ok', 'Ok', 'Ok', 'Ok'], 'ChargeCurentAlarm': 'Ok', 'ModuleVoltageAlarm': 'Ok', 'DischargeCurrentAlarm': 'Ok', 'Status1': 0, 'Status2': 14, 'Status3': 0, 'Status4': 0, 'Status5': 0}]}



    def threadMethod(self):
        try:
            data = self.p.update()
            if self.timerExists("timeoutPylontechRead"):
                self.timer(name = "timeoutPylontechRead",remove = True)
            valueList = []
            for module in data["AnaloglList"]:
                valueList += module["CellVoltages"]
            self.BmsWerte["Vmin"] = min(valueList)
            self.BmsWerte["Vmax"] = max(valueList)
            valueList = []
            for module in data["AnaloglList"]:
                valueList += module["Temperatures"]
            self.BmsWerte["Tmin"] = min(valueList)
            self.BmsWerte["Tmax"] = max(valueList)
    
            self.BmsWerte["Current"] = 0.0
            for module in data["AnaloglList"]:
                self.BmsWerte["Current"] += module["Current"]
    
            self.BmsWerte["BmsEntladeFreigabe"] = True
            self.BmsWerte["BmsLadeFreigabe"] = True
            for module in data["AlarmInfoList"]:
                #if not data["ChargeDischargeManagementList"]["StatusDischargeEnable"]:
                if module["ModuleVoltageAlarm"] != "Ok":
                    if self.BmsWerte["Vmin"] < 3.0:
                        self.BmsWerte["BmsEntladeFreigabe"] = False
                    if self.BmsWerte["Vmax"] > 3.5:
                        self.BmsWerte["BmsLadeFreigabe"] = False
                for cellAlarm in module["CellAlarm"]:
                    if cellAlarm != "Ok":
                        if self.BmsWerte["Vmin"] < 3.0:
                            self.BmsWerte["BmsEntladeFreigabe"] = False
                        if self.BmsWerte["Vmax"] > 3.5:
                            self.BmsWerte["BmsLadeFreigabe"] = False
    
            for module in data["ChargeDischargeManagementList"]:
                if module["StatusFullChargeRequired"]:
                    self.BmsWerte["FullChargeRequired"] = True
    
            self.BmsWerte["Prozent"] = data["Calculated"]["Remain_Percent"]
            self.BmsWerte["Ah"] = data["Calculated"]["RemainCapacity_Ah"]
            self.BmsWerte["Power"] = data["Calculated"]["Power_W"]
    
            self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
    
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)
        except:
            self.logger.error(self, f"Error reading {self.name} inteface.")
            if self.timer(name = "timeoutPylontechRead", timeout = 60):
                raise Exception(f'{self.name} connection is broken since 60s!')

    def threadBreak(self):
        time.sleep(1.5)