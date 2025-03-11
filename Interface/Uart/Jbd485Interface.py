from Base.InterfaceBase import InterfaceBase
import time
from GridLoad.SocMeter import SocMeter
import serial
import json
from Interface.Uart.Jbd.jbd import JBDUP
from Base.Supporter import Supporter

class Jbd485Interface(InterfaceBase):
    '''
    classdocs
    '''
    
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.BmsWerte = {"VoltageList":[], "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "FullChargeRequired":False, "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False, "BmsLadeFreigabe": False}
        self.CHG_FET_DISABLE_TIME = 60*60*3
        self.FULL_CHG_REQ_TIMER = 60*60*24*30
        self.CHARGE_FET_RECOVER_VOLTAGE = 3.40

    def handleChargeFet(self, chgFetState, maxCellVoltage):
        # We count charge fet disables, if we reached 5 disables we deactivate charge fet for 60min. 
        # This funktion is to prevent a oscillating system because of debalanced cells ect

        # detect falling edge
        if not chgFetState and self.old_dsg_fet_en:
            self.chg_fet_disable_count += 1

        self.old_dsg_fet_en = chgFetState

        # if 3 falling edges were detected we start a timer and deactivate chg fet
        if self.chg_fet_disable_count >= 3:
            if self.timerExists("chgFetDisable"):
                if self.timer(name = "chgFetDisable", timeout = self.CHG_FET_DISABLE_TIME) or (maxCellVoltage < self.CHARGE_FET_RECOVER_VOLTAGE):
                    self.jbd.chgDsgEnable(chgEnable=True, dsgEnable=True)
                    self.timer("chgFetDisable", remove=True)
                    self.chg_fet_disable_count = 0
                    self.logger.info(self, f"{self.name} inteface enabled charge fet from BMS")
            else:
                self.jbd.chgDsgEnable(chgEnable=False, dsgEnable=True)
                self.timer(name = "chgFetDisable", timeout = self.CHG_FET_DISABLE_TIME)
                self.logger.info(self, f"{self.name} inteface disabled charge fet from BMS")
        # reset counter after 1 day
        if self.timer(name = "reset_disable_counter", startTime = Supporter.getTimeOfToday(hour = 20), timeout = 60*60*24):
            self.chg_fet_disable_count = 0

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "battCount"])
        self.tagsIncluded(["baudrate"], optional = True, default = 9600)
        #tries = 0
        #while tries < self.MAX_INIT_TRIES:
        #    try:
        #        
        #        self.p = PylontechStack(self.configuration["interface"], baud=self.configuration["baudrate"], manualBattcountLimit=self.configuration["battCount"])
        #        break
        #    except:
        #        time.sleep(10)
        #        self.logger.info(self, f"Device --{self.name}-- {tries + 1} from {self.MAX_INIT_TRIES} inits failed.")
        #    tries += 1
        #if tries >= self.MAX_INIT_TRIES:
        #    raise Exception(f'{self.name} connection could not established! Check interface, baudrate, battCount!')

        self.serialConn = serial.Serial(
            port         = self.configuration["interface"],
            baudrate     = self.configuration["baudrate"],
        )
        self.jbd = JBDUP(self.serialConn)

        # Maybe the BMS is sleeping so we will wake it up here, but communication will fail.
        try:
            self.jbd.readBasicInfo()
        except:
            time.sleep(2)

        # self.jbd.readDeviceInfo()        # {'device_name': 'JBD-UP16S010-L16S-200A-B-R-C'}
        self.bmsName = self.jbd.readDeviceInfo()['device_name']
        self.logger.info(self, f"Bms: {self.bmsName} found")
        self.fullCap = self.jbd.readBasicInfo()["full_cap"]
        self.jbd.chgDsgEnable(chgEnable=True, dsgEnable=True)
        self.old_dsg_fet_en = True
        self.chg_fet_disable_count = 0

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "cmd" in newMqttMessageDict["content"]:
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    # Reset FullChgReqTimer because we are in Floatmode now
                    if self.timerExists("FullChgReqTimer"):
                        self.timer("FullChgReqTimer", remove=True)
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
            if basicInfo["full_cap"] != self.fullCap:
                self.logger.error(self, f'BMS changed full_cap from {self.fullCap} to {basicInfo["full_cap"]}')
                self.logger.error(self, f'{str(basicInfo)}')
                self.logger.error(self, f'{str(cellInfo)}')
                self.fullCap = basicInfo["full_cap"]
                self.logger.writeLogBufferToDisk(f"logfiles/{self.name}_full_cap_changed.log")
            for cell in list(cellInfo):
                self.BmsWerte["VoltageList"].append(cellInfo[cell] / 1000)
            self.BmsWerte["Current"] = basicInfo["pack_ma"] / 1000
            self.BmsWerte["Prozent"] = basicInfo["cap_pct"]
            self.chg_fet_en = basicInfo["chg_fet_en"]
            self.BmsWerte["BmsEntladeFreigabe"] = not (not basicInfo["dsg_fet_en"] or basicInfo["puv_alm"] or basicInfo["cuv_alm"])
            self.BmsWerte["BmsLadeFreigabe"] = not (not basicInfo["chg_fet_en"] or basicInfo["pov_alm"] or basicInfo["cov_alm"])
            self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
            if self.timerExists("timeoutJbdRead"):
                self.timer("timeoutJbdRead", remove=True)
            self.handleChargeFet(basicInfo["chg_fet_en"], max(self.BmsWerte["VoltageList"]))
        except:
            self.logger.error(self, f"Error reading {self.name} inteface.")
            if self.timer(name = "timeoutJbdRead", timeout = 60):
                raise Exception(f'{self.name} connection to bms: {self.bmsName} is broken since 60s!')

        # todo einzelne Packs falls nötig aus dem system nehmen um balancieren lassen
        # self.jbd.chgDsgEnable(chgEnable=False, dsgEnable=False)

        # If FullChgReqTimer is triggered we send one FullChargeRequired request
        if self.timer("FullChgReqTimer", timeout=self.FULL_CHG_REQ_TIMER):
            self.BmsWerte["FullChargeRequired"] = True

        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)

        if self.BmsWerte["FullChargeRequired"]:
            self.BmsWerte["FullChargeRequired"] = False

    def threadBreak(self):
        time.sleep(1.5)