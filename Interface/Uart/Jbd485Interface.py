from Base.InterfaceBase import InterfaceBase
import time
from GridLoad.SocMeter import SocMeter
import serial
import json
from Interface.Uart.Jbd.jbd import JBDUP

class Jbd485Interface(InterfaceBase):
    '''
    classdocs
    '''
    
    maxInitTries = 10

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.BmsWerte = {"VoltageList":[], "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False, "BmsLadeFreigabe": False}

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "battCount"])
        self.tagsIncluded(["baudrate"], optional = True, default = 9600)
        #self.tries = 0
        #while self.tries <= self.maxInitTries:
        #    self.tries += 1
        #    try:
        #        
        #        self.p = PylontechStack(self.configuration["interface"], baud=self.configuration["baudrate"], manualBattcountLimit=self.configuration["battCount"])
        #        break
        #    except:
        #        time.sleep(10)
        #        self.logger.info(self, f"Device --{self.name}-- {self.tries} from {self.maxInitTries} inits failed.")
        #       if self.tries >= self.maxInitTries:
        #           raise Exception(f'{self.name} connection could not established! Check interface, baudrate, battCount!')

        self.serialConn = serial.Serial(
            port         = self.configuration["interface"],
            baudrate     = self.configuration["baudrate"],
        )
        self.jbd = JBDUP(self.serialConn)

        # Maybe the BMS is sleeping so we will wake it up here, but communication will fail.
        try:
            self.jbd.readBasicInfo()
        except:
            pass

        # self.jbd.readDeviceInfo()        # {'device_name': 'JBD-UP16S010-L16S-200A-B-R-C'}
        self.bmsName = self.jbd.readDeviceInfo()['device_name']
        self.logger.info(self, f"Bms: {self.bmsName} found")
        self.fullCap = self.jbd.readBasicInfo()["full_cap"]

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():

            newMqttMessageDict = self.mqttRxQueue.get(block = False)

            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if "cmd" in newMqttMessageDict["content"]:
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    # reset battery pack to max capacity value if charge fet is on. Else ignore this cmd because battery is momentary not connected to system. 
                    if self.chg_fet_en:
                        try:
                            self.jbd.setPackCapRem(self.fullCap)
                        except:
                            self.logger.error(self, f"Could not set capacity of {self.bmsName}")
                    else:
                        self.logger.info(self, f"cmd >resetSoc< is ignored because charge fet is switched off!")

        try:
            basicInfo = self.jbd.readBasicInfo()         # {'pack_mv': 58170, 'pack_ma': 0, 'cur_cap': 290, 'full_cap': 550, 'cycle_cnt': 0, 'year': 2023, 'month': 7, 'day': 1, 'bal0': False, 'bal1': False, 'bal2': False, 'bal3': False, 'bal4': False, 'bal5': False, 'bal6': False, 'bal7': False, 'bal8': False, 'bal9': False, 'bal10': False, 'bal11': False, 'bal12': False, 'bal13': False, 'bal14': True, 'bal15': False, 'bal16': False, 'bal17': False, 'bal18': False, 'bal19': False, 'bal20': False, 'bal21': False, 'bal22': False, 'bal23': False, 'bal24': False, 'bal25': False, 'bal26': False, 'bal27': False, 'bal28': False, 'bal29': False, 'bal30': False, 'bal31': False, 'covp_err': False, 'cuvp_err': False, 'povp_err': False, 'puvp_err': False, 'chgot_err': False, 'chgut_err': False, 'dsgot_err': False, 'dsgut_err': False, 'chgoc_err': False, 'dsgoc_err': False, 'sc_err': False, 'afe_err': False, 'software_err': False, 'airot_err': False, 'airut_err': False, 'pcbot_err': False, 'cuv_alm': False, 'cov_alm': False, 'puv_alm': False, 'pov_alm': False, 'chgoc_alm': False, 'dsgoc_alm': False, 'chgot_alm': False, 'chgut_alm': False, 'dsgot_alm': False, 'dsgut_alm': False, 'airot_alm': False, 'airut_alm': False, 'pcbot_alm': False, 'cdiff_alm': False, 'socl_alm': False, 'na_alm': False, 'version': 40, 'cap_pct': 53, 'chg_fet_en': True, 'dsg_fet_en': True, 'ntc_cnt': 4, 'cell_cnt': 15, 'ntc_board': 26.3, 'ntc_air': 26.0, 'ntc0': 24.1, 'ntc1': 23.9, 'ntc2': 24.0, 'ntc3': 24.3, 'ntc4': None, 'ntc5': None, 'ntc6': None, 'ntc7': None, 'alarm_raw': 0, 'fault_raw': 0, 'bal_raw': 16384}
            cellInfo = self.jbd.readCellInfo()          # {'cell0_mv': 3875, 'cell1_mv': 3878, 'cell2_mv': 3879, 'cell3_mv': 3877, 'cell4_mv': 3873, 'cell5_mv': 3882, 'cell6_mv': 3879, 'cell7_mv': 3879, 'cell8_mv': 3871, 'cell9_mv': 3869, 'cell10_mv': 3878, 'cell11_mv': 3872, 'cell12_mv': 3877, 'cell13_mv': 3881, 'cell14_mv': 3893}
            self.BmsWerte["VoltageList"] = []
            for cell in list(cellInfo):
                self.BmsWerte["VoltageList"].append(cellInfo[cell] / 1000)
            self.BmsWerte["Current"] = basicInfo["pack_ma"] / 1000
            self.BmsWerte["Prozent"] = basicInfo["cap_pct"]
            self.fullCap = basicInfo["full_cap"]
            self.chg_fet_en = basicInfo["chg_fet_en"]
            self.BmsWerte["BmsEntladeFreigabe"] = not (not basicInfo["dsg_fet_en"] or basicInfo["puv_alm"] or basicInfo["cuv_alm"])
            self.BmsWerte["BmsLadeFreigabe"] = not (not basicInfo["chg_fet_en"] or basicInfo["pov_alm"] or basicInfo["cov_alm"])
            self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
        except Exception as e:
            self.logger.error(self, f"Error reading {self.name} inteface.")
            self.logger.error(self, e)
            if self.timer(name = "timeoutPylontechRead", timeout = 60):
                raise Exception(f'{self.name} connection to bms: {self.bmsName} is broken since 60s!')

        # todo einzelne Packs falls nötig aus dem system nehmen um balancieren lassen
        # self.jbd.chgDsgEnable(chgEnable=False, dsgEnable=False)

        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)


    def threadBreak(self):
        time.sleep(1.5)