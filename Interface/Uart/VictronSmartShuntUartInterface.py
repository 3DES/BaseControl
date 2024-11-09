import time
import json
import re
from Base.Supporter import Supporter
import functools

from GridLoad.SocMeter import SocMeter
from Interface.Uart.BasicUartInterface import BasicUartInterface

class VictronSmartShuntUartInterface(BasicUartInterface):
    '''
    classdocs
    '''
    MATCHED_KEYS = sorted(["I", "SOC", "V", "Alarm", "AR", "H4", "H5", "H6", "H7", "H8"])     # "T"
    
    
    CURRENT_TEXT         = "Current"        # "I"
    PERCENT_TEXT         = "Prozent"        # "SOC"
    VOLTAGE_TEXT         = "Voltage"        # "V"
    ALARM_TEXT           = "Alarm"          # "Alarm"
    ALARM_REASON_TEXT    = "AlarmReason"    # "AR"
    CHARGE_CYCLES_TEXT   = "ChargeCycles"   # "H4"
    FULL_DISCHARGES_TEXT = "FullDischarges" # "H5"
    AH_DRAWN_TEXT        = "Ah"             # "H6"
    MIN_VOLTAGE_TEXT     = "VminAccu"       # "H7"
    MAX_VOLTAGE_TEXT     = "VmaxAccu"       # "H8"


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

        self.tagsIncluded("readTimeout", optional = True, default = 20)
        self.READ_TIMEOUT = self.configuration["readTimeout"]     # tries to read valid values for up to 20 or more seconds


    def matchBuffer(self):
        if not self.initialChecksumFound:
            if matches := re.search(b".*Checksum\t.(?P<remaining>\r\n.*)", self.data, re.DOTALL):
                self.data = matches.group("remaining")
                self.initialChecksumFound = True
        else:
            if matches := re.search(b"(?P<block>.+?Checksum\t.)(?P<remaining>\r\n.*)", self.data, re.DOTALL):
                currentBlock = matches.group("block")
                self.data = matches.group("remaining")      # remove matched block from data
                
                # calculate checksum (simple BCC -> 0x00 - "sum of all elements including lead-in \r\n but exclusive checksum")
                # the following lines show how this works:  
                #     data=b'\r\nH1\t-46788\r\nH2\t-445\r\nH3\t0\r\nH4\t0\r\nH5\t0\r\nH6\t-76923\r\nH7\t5610\r\nH8\t56605\r\nH9\t2225\r\nH10\t0\r\nH11\t17\r\nH12\t0\r\nH15\t0\r\nH16\t0\r\nH17\t394\r\nH18\t2478\r\nChecksum\t\x82'
                #     summ = 0
                #     for char in data:
                #         summ += int(char)
                #     # empty line to paste this directly into the interpreter
                #     summ &= 0xFF
                #     print("" + ("in" if summ else "") + f"valid checksum 0x{summ:02X}")
                calculatedChecksum = 0
                for char in currentBlock:
                    calculatedChecksum += int(char)
                calculatedChecksum &= 0xFF

                # result must be zero if block is valid since last element is checksum and 0x00 - "sum of all elements including lead-in \r\n but exclusive checksum") + checksum is 0x00
                if (calculatedChecksum == 0x00):
                    for key in self.MATCHED_KEYS:
                        # a key always consists of \r\n as lead-in, the key itself, a \t and a value, the next \r\n already belongs to the next key
                        matchString = bytes(f"\r\n{key}\t(?P<value>[^\r]+)", "utf-8")
                        if matches := re.search(matchString, currentBlock):
                            self.matchedValues[key] = matches.group("value")
                else:
                    self.logger.warning(self, f"received Victron message with invalid checksum [{currentBlock}]")


    def prepareHomeAutomation(self, force : bool = False):
        # ensure all needed keys have already been prepared, otherwise return with False
        keys = [self.CURRENT_TEXT, self.PERCENT_TEXT, self.VOLTAGE_TEXT, self.ALARM_TEXT, self.ALARM_REASON_TEXT, self.CHARGE_CYCLES_TEXT, self.FULL_DISCHARGES_TEXT, self.AH_DRAWN_TEXT, self.MIN_VOLTAGE_TEXT, self.MAX_VOLTAGE_TEXT]

        for key in keys:
            if key not in self.SocMonitorWerte:
                #Supporter.debugPrint(f"{key} is still missed in self.energyData!", color = "RED")
                return False

        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_TEXT,         self.SocMonitorWerte[self.CURRENT_TEXT],                                 compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.PERCENT_TEXT,         self.SocMonitorWerte[self.PERCENT_TEXT],         compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.VOLTAGE_TEXT,         self.SocMonitorWerte[self.VOLTAGE_TEXT],         compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = .2), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.ALARM_TEXT,           self.SocMonitorWerte[self.ALARM_TEXT],           compareValue = changed, compareMethod = lambda a, b: a != b,                                          force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.ALARM_REASON_TEXT,    self.SocMonitorWerte[self.ALARM_REASON_TEXT],    compareValue = changed, compareMethod = lambda a, b: a != b,                                          force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CHARGE_CYCLES_TEXT,   self.SocMonitorWerte[self.CHARGE_CYCLES_TEXT],   compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.FULL_DISCHARGES_TEXT, self.SocMonitorWerte[self.FULL_DISCHARGES_TEXT], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.AH_DRAWN_TEXT,        self.SocMonitorWerte[self.AH_DRAWN_TEXT],        compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.MIN_VOLTAGE_TEXT,     self.SocMonitorWerte[self.MIN_VOLTAGE_TEXT],     compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1),  force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.MAX_VOLTAGE_TEXT,     self.SocMonitorWerte[self.MAX_VOLTAGE_TEXT],     compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1),  force = force)

        return changed


    def publishHomeAutomation(self):
        self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True, enableEcho = False)


    def threadSimmulationSupport(self):
        '''
        Necessary since this thread supports SIMULATE flag
        '''
        pass


    def threadInitMethod(self):
        self.homeAutomationValues = { self.CURRENT_TEXT : 0,   self.PERCENT_TEXT : 0,   self.VOLTAGE_TEXT : 0,   self.ALARM_TEXT : 0,      self.ALARM_REASON_TEXT : "---",  self.CHARGE_CYCLES_TEXT : 0,      self.FULL_DISCHARGES_TEXT : 0,      self.AH_DRAWN_TEXT : 0,    self.MIN_VOLTAGE_TEXT : 0,   self.MAX_VOLTAGE_TEXT : 0 }
        homeAutomationUnits       = { self.CURRENT_TEXT : "A", self.PERCENT_TEXT : "%", self.VOLTAGE_TEXT : "V", self.ALARM_TEXT : "none", self.ALARM_REASON_TEXT : "none", self.CHARGE_CYCLES_TEXT : "none", self.FULL_DISCHARGES_TEXT : "none", self.AH_DRAWN_TEXT : "Ah", self.MIN_VOLTAGE_TEXT : "V", self.MAX_VOLTAGE_TEXT : "V" }
        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomationTopic = self.homeAutomation.mqttDiscoverySensor(self.homeAutomationValues, unitDict = homeAutomationUnits, subTopic = "homeautomation")

        # no initial publish in that case since old values are OK if there are some already
        #self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True, enableEcho = False)

        # call super method to get serial interface initialized
        super().threadInitMethod()


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
            self.flush()       # clear serial pipe to get current values and not old ones
            while sorted(list(self.matchedValues.keys())) != self.MATCHED_KEYS:
                self.data += self.serialRead(length = DEFAULT_READ_LENGTH, timeout = timeout)
                self.matchBuffer()

                if self.timer(name = "readValues", timeout = self.READ_TIMEOUT):
                    raise Exception(f"Reading Victron values timed out after {self.READ_TIMEOUT} seconds")
            #Supporter.debugPrint(f"matched Victron values: {self.matchedValues}")
            self.timer(name = "readValues", remove = True)
        else:
            # simulation mode, so simulate some values
            self.matchedValues = {
                "I":     2000,              # 2000 mA
                "SOC":   650,               # state of charge at 650 per mille
                "V":     52000,             # 52000 mV
                "Alarm": "",                # no alarm
                "AR":    0,                 # no alarm reason
                "H4":    217,               # charge cycles
                "H5":    5,                 # full discharges
                "H6":    37000,             # 37 Ah
                "H7":    51000,             # Vmin
                "H8":    53000              # Vmax
            }

        self.SocMonitorWerte[self.CURRENT_TEXT]         = round(int(self.matchedValues["I"]) / 1000, 2)
        self.SocMonitorWerte[self.PERCENT_TEXT]         = int(self.matchedValues["SOC"]) / 10
        self.SocMonitorWerte[self.VOLTAGE_TEXT]         = round(int(self.matchedValues["V"]) / 1000, 2)
        self.SocMonitorWerte[self.ALARM_TEXT]           = str(self.matchedValues["Alarm"])
        self.SocMonitorWerte[self.ALARM_REASON_TEXT]    = str(self.matchedValues["AR"])
        self.SocMonitorWerte[self.CHARGE_CYCLES_TEXT]   = int(self.matchedValues["H4"])
        self.SocMonitorWerte[self.FULL_DISCHARGES_TEXT] = int(self.matchedValues["H5"])
        self.SocMonitorWerte[self.AH_DRAWN_TEXT]        = round(int(self.matchedValues["H6"]) / 1000, 2)
        self.SocMonitorWerte[self.MIN_VOLTAGE_TEXT]     = round(int(self.matchedValues["H7"]) / 1000, 2)
        self.SocMonitorWerte[self.MAX_VOLTAGE_TEXT]     = round(int(self.matchedValues["H8"]) / 1000, 2)

        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = False, enableEcho = False)

        if self.prepareHomeAutomation():
            #Supporter.debugPrint(f"{self.homeAutomationValues}", color = "LIGHTRED")
            self.logger.warning(self, f"read Victron values {self.homeAutomationValues}")
            self.publishHomeAutomation()


    def threadBreak(self):
        time.sleep(5)
