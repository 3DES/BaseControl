import time
import json
import re
from Base.Supporter import Supporter

from GridLoad.SocMeter import SocMeter
from Interface.Uart.BasicUartInterface import BasicUartInterface

class VictronSmartShuntUartInterface(BasicUartInterface):
    '''
    classdocs
    '''
    MATCHED_KEYS = sorted(["I", "SOC", "V", "Alarm", "AR", "H4", "H5", "H6", "H7", "H8"])     # "T"
    
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.SocMonitorWerte = {"Current":0, "Prozent":SocMeter.InitAkkuProz}
        self.cmdList = []       # @todo brauchen wir diese Variable?

        self.matchedValues = {}
        self.data = b""     # bytearray("")
        self.initialChecksumFound = False
        
        self.READ_TIMEOUT = 20      # tries to read valid values for up to 20 seconds


    def matchBuffer(self):
        if not self.initialChecksumFound:
            if matches := re.search(b"Checksum\t.\r\n(?P<remaining>.*)", self.data, re.DOTALL):
                self.data = matches.group("remaining")
                self.initialChecksumFound = True
        else:
            if matches := re.search(b"(?P<block>.+?)Checksum\t(?P<checksum>.)\r\n(?P<remaining>.*)", self.data, re.DOTALL):
                currentBlock = matches.group("block")
                checksum = matches.group("checksum")
                self.data = matches.group("remaining")
                for key in self.MATCHED_KEYS:
                    matchString = bytes(f"{key}\t(?P<value>[^\r]+)\r\n", "utf-8")
                    if matches := re.search(matchString, currentBlock):
                        self.matchedValues[key] = matches.group("value")


    def threadMethod(self):
        DEFAULT_READ_LENGTH = 20
        timeout = 1

        self.matchedValues = {}
        self.data = b""
        self.initialChecksumFound = False

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)
            if "cmd" in newMqttMessageDict["content"]:
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    # @todo Victron resetten, falls das über die Kommunikationsschnittstelle irgendwie möglich ist, ggf. ist das auch garnicht nötig, wenn sich der Victron Shunt selbst beim Erreichen der Max.Spg. selbst resettet
                    pass
        
        self.serialReset_input_buffer()

        if not self.toSimulate():
            # get real values from victron shunt
            while sorted(list(self.matchedValues.keys())) != self.MATCHED_KEYS:
                self.data += self.serialRead(length = DEFAULT_READ_LENGTH, timeout = timeout)
                self.matchBuffer()
    
                if self.timer(name = "readValues", timeout = self.READ_TIMEOUT):
                    raise Exception(f"Reading Victron values timed out after {self.READ_TIMEOUT} seconds")
            self.timer(name = "readValues", remove = True)
        else:
            # simulation mode, so simulate some values
            self.matchedValues = {
                "I":     2000,              # 2000 mA
                "SOC":   650,               # state of charge at 650 per mille
                "V":     52000,             # 52000 mV
                "Alarm": "",                # no alarm
                "AR":    0,                 # no alarm reason
                "H4":    217,               # charge cyclces
                "H5":    5,                 # full discharges
                "H6":    37000,             # 37 Ah
                "H7":    51000,             # Vmin
                "H8":    53000              # Vmax
            }

        self.SocMonitorWerte["Current"]        = round(int(self.matchedValues["I"]) / 1000, 2)
        self.SocMonitorWerte["Prozent"]        = int(self.matchedValues["SOC"]) / 10
        self.SocMonitorWerte["Voltage"]        = round(int(self.matchedValues["V"]) / 1000, 2)
        self.SocMonitorWerte["Alarm"]          = str(self.matchedValues["Alarm"])
        self.SocMonitorWerte["AlarmReason"]    = str(self.matchedValues["AR"])
        self.SocMonitorWerte["ChargeCycles"]   = str(self.matchedValues["H4"])
        self.SocMonitorWerte["FullDischarges"] = str(self.matchedValues["H5"])
        self.SocMonitorWerte["Ah"]             = round(int(self.matchedValues["H6"]) / 1000, 2)
        self.SocMonitorWerte["VminAccu"]       = round(int(self.matchedValues["H7"]) / 1000, 2)
        self.SocMonitorWerte["VmaxAccu"]       = round(int(self.matchedValues["H8"]) / 1000, 2)

        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = False, enableEcho = False)
    
