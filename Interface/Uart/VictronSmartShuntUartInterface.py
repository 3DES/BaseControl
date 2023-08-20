import time
import json
import re

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
        self.cmdList = []

        self.matchedValues = {}
        self.data = b""     # bytearray("")
        self.initialChecksumFound = False


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

        self.serialReset_input_buffer()

        while sorted(list(self.matchedValues.keys())) != self.MATCHED_KEYS:
            self.data += self.serialRead(length = DEFAULT_READ_LENGTH, timeout = timeout)
            self.matchBuffer()

            if self.timer(name = "readValues", timeout = 20):
                raise Exception("Reading Victron values timed out after 20 seconds")

        self.timer(name = "readValues", remove = True)

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
    
