import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
from Base.CEnum import CEnum
import Base
import subprocess
import Base.Crc
from queue import Queue
import colorama
import functools


import sys
import re


class MeanWellNPB(ThreadObject):
    '''
    classdocs
    
    MeanWell factory reset:
     1) set all DIP switches to ON before applying AC main
     2) apply AC main under remote OFF condition
     3) switch all DIP switches to OFF and back to ON within 15 seconds
     4) green LED flashes 3 times if reset was successful
     5) remote ON the unit and it's now back to factory settings
    '''


    # some small tests, but no automatic tests, they have to be checked manually!
    TEST_STATE_HANDLING   = False
    TEST_SURPLUS_HANDLING = False   # only works if TEST_STATE_HANDLING is set to False


    def _convertFirmwareRevision(self, command : str, data : bytes, reverse : bool = False):
        '''
        Converts Meanwell charger firmware revision to integer, e.g. b"0D0BFF..FF" -> 0x0B0D = 2829
        @param command    command for the case different commands need different conversions
        @param data       data to be converted
        @param reverse    False means data from Meanwell charger to e.g. power controller, True means data from power controller to Meanwell charger 
        '''
        # 0000   1b 00 10 70 df f9 07 e1 ff ff 00 00 00 00 09 00   ...p............
        # 0010   01 04 00 10 00 81 03 1b 00 00 00 54 30 30 30 43   ...........T000C
        # 0020   30 30 30 33 38 38 34 30 30 30 44 30 42 46 46 46   0003884000D0BFFF
        # 0030   46 46 46 46 46 0d                                 FFFFF.

        if reverse:
            pass
        else:
            # reverse data but stop when "FF" has been found
            reversedData = Supporter.changeByteOrderOfHexString(hexString = data, stopCharacters = [b"FF"])
        return int(reversedData,16)


    def _convertHexValue(self, command : str, data : bytes, reverse : bool = False):
        '''
        Converts bytes hex string to length formated hex string with correct byte order, e.g. b'ABCD' -> "0xCDAB" 
        @param command    command for the case different commands need different conversions
        @param data       data to be converted
        @param reverse    False means data from Meanwell charger to e.g. power controller, True means data from power controller to Meanwell charger 
        '''
        if reverse:
            pass
        else:
            dataInt = int(Supporter.changeByteOrderOfHexString(data), 16)
            dataString = "0x{data:0{width}X}".format(data = dataInt, width = self.CAN_COMMANDS[command]["bytes"] * 2)
        return dataString


    class CAN_COMMAND_NAMES(CEnum):
        OPERATION        = "OPERATION"
        VOUT_SET         = "VOUT_SET"
        IOUT_SET         = "IOUT_SET"
        FAULT_STATUS     = "FAULT_STATUS"
        READ_VIN         = "READ_VIN"
        READ_VOUT        = "READ_VOUT"
        READ_IOUT        = "READ_IOUT"
        READ_TEMP        = "READ_TEMP"
        ID1              = "ID1"                   # ID, ID1 and ID2 will always execute ID1 and ID2
        ID2              = "ID2"
        MODEL1           = "MODEL1"                # MODEL, MODEL1 and MODEL2 will always execute MODEL1 and MODEL2
        MODEL2           = "MODEL2"
        FW_VERSION       = "FW_VERSION"
        LOCATION         = "LOCATION"
        DATE             = "DATE"
        SERIAL1          = "SERIAL1"               # SERIAL, SERIAL1 and SERIAL2 will always execute SERIAL1 and SERIAL2
        SERIAL2          = "SERIAL2"
        CURVE_CC         = "CURVE_CC"
        CURVE_CV         = "CURVE_CV"
        CURVE_FV         = "CURVE_FV"
        CURVE_TC         = "CURVE_TC"
        CURVE_CFG        = "CURVE_CFG"
        CURVE_CC_TIMEOUT = "CURVE_CC_TIMEOUT"
        CURVE_CV_TIMEOUT = "CURVE_CV_TIMEOUT"
        CURVE_FV_TIMEOUT = "CURVE_FV_TIMEOUT"
        CHG_STATUS       = "CHG_STATUS"
        #CHG_RST_VBAT     = "CHG_RST_VBAT"        # get no answer!
        SCALING_FACTOR   = "SCALING_FACTOR"
        SYSTEM_STATUS    = "SYSTEM_STATUS"
        SYSTEM_CONFIG    = "SYSTEM_CONFIG"

    CAN_COMMANDS = {
        # some of the commands, e.g. DATE, LOCATION or SERIAL are readable and writable but that is not supported here!
        # furthermore, commands with trailing digits, e.g. SERIAL1, MODEL1, ... are only supported as readable!
        # "resolution" is the exponent of 10^x, so 0 = 1, 1 = 10, 2 = 100, None = None
        # "type" can be str, int or a function expecting at least "command", "data" and "reverse" parameters
        CAN_COMMAND_NAMES.OPERATION        : {"opcode" : 0x0000, "valueName" : "operationMode",          "readOnly" : False, "bytes" : 1, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.VOUT_SET         : {"opcode" : 0x0020, "valueName" : "vOut",                   "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "V", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.IOUT_SET         : {"opcode" : 0x0030, "valueName" : "cOut",                   "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "A", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.FAULT_STATUS     : {"opcode" : 0x0040, "valueName" : "faultState",             "readOnly" : True,  "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertHexValue},            # should be handled as hex string, so single bits are more readable!
        CAN_COMMAND_NAMES.READ_VIN         : {"opcode" : 0x0050, "valueName" : "vIn",                    "readOnly" : True,  "bytes" : 2, "resolution" :    1, "unit" :   "V", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.READ_VOUT        : {"opcode" : 0x0060, "valueName" : "vOutReadback",           "readOnly" : True,  "bytes" : 2, "resolution" :    2, "unit" :   "V", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.READ_IOUT        : {"opcode" : 0x0061, "valueName" : "cOutReadback",           "readOnly" : True,  "bytes" : 2, "resolution" :    2, "unit" :   "A", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.READ_TEMP        : {"opcode" : 0x0062, "valueName" : "temperature",            "readOnly" : True,  "bytes" : 2, "resolution" :    1, "unit" :  "°C", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.ID1              : {"opcode" : 0x0080, "valueName" : "manufacturer",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.ID2              : {"opcode" : 0x0081, "valueName" : "manufacturer",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.MODEL1           : {"opcode" : 0x0082, "valueName" : "chargerModel",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.MODEL2           : {"opcode" : 0x0083, "valueName" : "chargerModel",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.FW_VERSION       : {"opcode" : 0x0084, "valueName" : "firmware",               "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertFirmwareRevision},    # has to be handled in a special way since firmware revision contains 0xFFs as end tags
        CAN_COMMAND_NAMES.LOCATION         : {"opcode" : 0x0085, "valueName" : "manufacturingLocation",  "readOnly" : True,  "bytes" : 3, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.DATE             : {"opcode" : 0x0086, "valueName" : "manufacturingDate",      "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.SERIAL1          : {"opcode" : 0x0087, "valueName" : "serialNumber",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.SERIAL2          : {"opcode" : 0x0088, "valueName" : "serialNumber",           "readOnly" : True,  "bytes" : 6, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : str},
        CAN_COMMAND_NAMES.CURVE_CC         : {"opcode" : 0x00B0, "valueName" : "constantCurrent",        "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "A", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_CV         : {"opcode" : 0x00B1, "valueName" : "constantVoltage",        "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "V", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_FV         : {"opcode" : 0x00B2, "valueName" : "floatVoltage",           "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "V", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_TC         : {"opcode" : 0x00B3, "valueName" : "tapperCurrent",          "readOnly" : False, "bytes" : 2, "resolution" :    2, "unit" :   "A", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_CFG        : {"opcode" : 0x00B4, "valueName" : "curveConfig",            "readOnly" : False, "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertHexValue},            # should be handled as hex string, so single bits are more readable!
        CAN_COMMAND_NAMES.CURVE_CC_TIMEOUT : {"opcode" : 0x00B5, "valueName" : "constantCurrentTimeout", "readOnly" : False, "bytes" : 2, "resolution" :    0, "unit" : "min", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_CV_TIMEOUT : {"opcode" : 0x00B6, "valueName" : "constantVoltageTimeout", "readOnly" : False, "bytes" : 2, "resolution" :    0, "unit" : "min", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CURVE_FV_TIMEOUT : {"opcode" : 0x00B7, "valueName" : "floatVoltageTimeout",    "readOnly" : False, "bytes" : 2, "resolution" :    0, "unit" : "min", "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.CHG_STATUS       : {"opcode" : 0x00B8, "valueName" : "chargingState",          "readOnly" : True,  "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertHexValue},            # should be handled as hex string, so single bits are more readable!
        #CAN_COMMAND_NAMES.CHG_RST_VBAT     : {"opcode" : 0x00B9, "valueName" : "chargingRestartVoltage", "readOnly" : False, "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : int},       # get no answer!?
        CAN_COMMAND_NAMES.SCALING_FACTOR   : {"opcode" : 0x00C0, "valueName" : "scalingRatio",           "readOnly" : True,  "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : int},
        CAN_COMMAND_NAMES.SYSTEM_STATUS    : {"opcode" : 0x00C1, "valueName" : "systemState",            "readOnly" : True,  "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertHexValue},            # should be handled as hex string, so single bits are more readable!
        CAN_COMMAND_NAMES.SYSTEM_CONFIG    : {"opcode" : 0x00C2, "valueName" : "systemConfig",           "readOnly" : False, "bytes" : 2, "resolution" : None, "unit" :  None, "errorOnNoResponse" : True, "type" : _convertHexValue},            # should be handled as hex string, so single bits are more readable!
    }
 
    # 0x0040 bits:
    # if "message" contains a list each list entry belongs to value, so 0x00 = entry[0], 0x01 = entry [1], ... there must be as many entries as possible bit values, e.g. 2 bits means 4 entries, etc.
    # if "message" contains only a simple string it always belongs to value != 0x00, in case of multi-bit entries the string is 
    FAULT_STATUS = {
        0x0001 <<  0 : None,
        0x0001 <<  1 : {"message" : "over temperature warning",  "type" : "warning"},
        0x0001 <<  2 : {"message" : "output over voltage",       "type" : "error"},
        0x0001 <<  3 : {"message" : "output over current",       "type" : "error"},
        0x0001 <<  4 : {"message" : "output short circuit",      "type" : "error"},
        0x0001 <<  5 : {"message" : "input voltage error",       "type" : "error"},
        0x0001 <<  6 : {"message" : "output turned OFF",         "type" : "info"},
        0x0001 <<  7 : {"message" : "internal high temperature", "type" : "error"},
    }

    # 0x00B4 bits:
    CURVE_CONFIG = {
        0x0003 <<  0 : {"message" : ["custom curve", "curve #1", "curve #2", "curve #3"],                                                             "type" : "info"},
        0x0003 <<  2 : {"message" : ["temp. compensation disabled", "temp. compensation -3mV", "temp. compensation -4mV", "temp. compensation -5mV"], "type" : "info"},
        0x0001 <<  4 : None,                                                                                                                          
        0x0001 <<  5 : None,                                                                                                                          
        0x0001 <<  6 : None,                                                                                                                          
        0x0001 <<  7 : {"message" : ["PSU mode", "charger mode"],                                                                                     "type" : "info"},                                                                             
                                                                                                                                                      
        0x0001 <<  8 : {"message" : "temperature compensation short circuit",                                                                         "type" : "info"},                                                                            
        0x0001 <<  9 : {"message" : "no battery detected",                                                                                            "type" : "warning"},                                                                            
        0x0001 << 10 : {"message" : "temperature compensation short circuit",                                                                         "type" : "info"},   
        0x0001 << 11 : {"message" : "no battery detected",                                                                                            "type" : "warning"},
        0x0001 << 12 : None,
        0x0001 << 13 : None,
        0x0001 << 14 : None,
        0x0001 << 15 : None,
    }

    # 0x00B8 bits:
    CHARGING_STATUS = {
        0x0001 <<  0 : {"message" : "fully charged",                          "type" : "info"},
        0x0001 <<  1 : {"message" : "constant current mode active",           "type" : "info"},
        0x0001 <<  2 : {"message" : "constant voltage mode active",           "type" : "info"},
        0x0001 <<  3 : {"message" : "float mode active",                      "type" : "info"},
        0x0001 <<  4 : None,
        0x0001 <<  5 : None,
        0x0001 <<  6 : {"message" : "wake up not yet finished",               "type" : "info"},
        0x0001 <<  7 : None,

        0x0001 <<  8 : None,
        0x0001 <<  9 : None,
        0x0001 << 10 : {"message" : "temperature compensation short circuit", "type" : "info"},   
        0x0001 << 11 : {"message" : "no battery detected",                    "type" : "warning"},
        0x0001 << 12 : None,
        0x0001 << 13 : {"message" : "constant current mode timeout",          "type" : "warning"},
        0x0001 << 14 : {"message" : "constant voltage mode timeout",          "type" : "warning"},
        0x0001 << 15 : {"message" : "float mode timeout",                     "type" : "warning"},
    }

    # 0x00C1 bits:
    SYSTEM_STATUS = {
        0x0001 <<  0 : None,
        0x0001 <<  1 : {"message" : "DC output too low",        "type" : "error"},
        0x0001 <<  2 : None,                                    
        0x0001 <<  3 : None,                                    
        0x0001 <<  4 : None,                                    
        0x0001 <<  5 : {"message" : "charger in initial state", "type" : "info"},
        0x0001 <<  6 : {"message" : "EEPROM access error",      "type" : "error"},
        0x0001 <<  7 : None,
    }

    # 0x00C2 bits:
    SYSTEM_CONFIG = {
        0x0001 <<  0 : None,
        0x0003 <<  1 : {"message" : ["power OFF", "power ON", "power on with last setting"], "type" : "info"},
        0x0001 <<  3 : None,
        0x0001 <<  4 : None,
        0x0001 <<  5 : None,
        0x0001 <<  6 : None,
        0x0001 <<  7 : None,
    }

    STATUS_ELEMENTS = {
        CAN_COMMAND_NAMES.FAULT_STATUS  : FAULT_STATUS,
        CAN_COMMAND_NAMES.CURVE_CFG     : CURVE_CONFIG,
        CAN_COMMAND_NAMES.CHG_STATUS    : CHARGING_STATUS,
        CAN_COMMAND_NAMES.SYSTEM_STATUS : SYSTEM_STATUS,
        CAN_COMMAND_NAMES.SYSTEM_CONFIG : SYSTEM_CONFIG,
    }

    CHARGER_ADDR_BASE    = 0x000C0000       # this is only the base address, the device address has to be added when the message is sent!
    CONTROLLER_ADDR_BASE = 0x000C0100       # this is only the base address, the device address has to be added when the message is sent!


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        # for easier interface message handling use an extra queue
        self.meanWellInterfaceQueue = Queue()

        # all messages published by our interfaces will be sent to our one interface queue
        super().__init__(threadName, configuration, {None : self.meanWellInterfaceQueue})

        # check and prepare mandatory parameters
        self.tagsIncluded(["mode", "voltageOut", "powerController", "powerControllerValue", "currentOutMin", "currentOutMax"])
        if self.configuration["mode"] != "PSU":
            raise Exception(f"chosen mode is \"{self.configuration['mode']}\" but only \"PSU\" is currently supported")
        self.tagsIncluded(["address"], intIfy = True)


    #def prepareHomeAutomation(self, force : bool = False):
    #    # ensure all needed keys have already been prepared, otherwise return with False
    #    keys = [self.RECEIVED_ENERGY_KEY, self.DELIVERED_ENERGY_KEY, self.CURRENT_POWER_KEY, self.CURRENT_POWER_L1_KEY, self.CURRENT_POWER_L2_KEY, self.CURRENT_POWER_L3_KEY, self.L1_VOLTAGE_KEY, self.L2_VOLTAGE_KEY, self.L3_VOLTAGE_KEY]
    #
    #    for key in keys:
    #        if key not in self.energyData:
    #            #Supporter.debugPrint(f"{key} is still missed in self.energyData!", color = "RED")
    #            return False
    #
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_OVERALL_TEXT,          self.energyData[self.RECEIVED_ENERGY_KEY],                          compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_OVERALL_TEXT,         self.energyData[self.DELIVERED_ENERGY_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_TEXT,             self.energyData[self.CURRENT_POWER_KEY],    compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L1_TEXT,          self.energyData[self.CURRENT_POWER_L1_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L2_TEXT,          self.energyData[self.CURRENT_POWER_L2_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L3_TEXT,          self.energyData[self.CURRENT_POWER_L3_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_LAST_15_MINUTES_TEXT, 0,                                          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)        # @todo sinnvollen Wert einfüllen!
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_LAST_15_MINUTES_TEXT,  0,                                          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)        # @todo sinnvollen Wert einfüllen!
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L1_TEXT,           self.energyData[self.L1_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L2_TEXT,           self.energyData[self.L2_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
    #    changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L3_TEXT,           self.energyData[self.L3_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
    #    return changed


    def _calculateSurplusCurrent(self, surplusPower : float, accumulatorVoltage : float, resolution : float = 1) -> float:#
        '''
        Calculates surplus current from surplus power and current accumulator voltage

        If surplus current cannot be calculated by dividing surplus power by accumulator voltage a proper resolution has to be given 
        
        @param surplusPower            surplus power value
        @param accumulatorVoltage      accumulator voltage
        @param resolution              multiplier to correct resolution if necessary
        @return                        calculated current as float value
        '''
        surplusCurrent = surplusPower / accumulatorVoltage * resolution
        if surplusCurrent < self.configuration["currentOutMin"]:
            surplusCurrent = 0.0    # it's not possible to set a current less than self.configuration["currentOutMin"] since Meanwell chargers don't support this so 0.0 means the charger has to be switched off 
        if surplusCurrent > self.configuration["currentOutMax"]:
            surplusCurrent = self.configuration["currentOutMax"]

        return surplusCurrent
        

    def _transmitCommand(self, command : str, address : str, data : str = None):
        self.mqttPublish(self.interfaceInTopics[0], {
            "cmd"     : command,
            "address" : address,
            "data"    : data
            },
            globalPublish = False,
            enableEcho = False)


    @classmethod
    def _cutTrailingDigits(cls, command : str):
        '''
        Cuts all trailing digits from given command and returns the result, if there is no digit the original command will be returned

        @param command   the command all trailing digits have to be removed
        @return          trimmed command or original command if there was no trailing digit
        '''
        regex = r"^([^\d]+)\d+$"
        if match := re.search(regex, command):
            command = match.group(1)
        return command


    @classmethod
    def _getTrailingDigits(cls, command : str):
        '''
        Returns trailing digits of given command and returns it, if there aren't any trailing digits zero will be returned instead
        
        @param command   the command the trailing digits should be taken and returned
        @return          trailing digits or 0 if there aren't any
        '''
        regex = r"^[^\d]+(\d+)$"
        digit = 0
        if match := re.search(regex, command):
            digit = int(match.group(1))
        return digit


    def _preProcessChargingData(self, chargingData : dict, previousData : dict = None) -> dict:
        '''
        Takes the charging data and tries to detect all changed bits that belong to states information. If there is any message defined the right one will be chosen and logged as specified.
        
        - Initially all bits are NEW ones
          - single-bit or single "string" entries have to be logged only if they are 1
          - multi-bit entries with "list" will be logged with their current state
        - if charging data and previous data has been given
          - single-bit or single "string" entries will be handled logged when their bits have been changed, "set" in case of != 0, "cleared" in case of 0
          - multi-bit entries with "list" will be logged when their bits have been changed with their current bits content as list index
        
        Furthermore, some states are handled directly and new values are added, e.g. "operation state" = ON/OFF will be added to get a readable operation state information 
        
        @param chargingData    dictionary with current data
        @param previousData    usually chargingData from last call but can be also None, it's not necessary that all entries from chargingData are also contained in previousData
        @return                dictionary containing all data from chargingData plus some added information
        '''
        def handleStateBits(stateDict : dict, currentBits : int, previousBits : int = None):
            '''
            Checks bits and prints the referring messages
            
            @param stateDict      status dictionary with entries that have to be checked
            @param currentBits    current bits states
            @param previousBits   previous bits states
            '''
            if currentBits == previousBits:
                raise Exception(f"handler called but there are no changed bits!")

            # handle all entries in given status dictionary
            for bitMask in stateDict.keys():
                # if entry in state dict is None it hasn't to be handled
                if stateDict[bitMask] is not None:
                    printMessage = ""
                    if type(stateDict[bitMask]["message"]) == str:
                        # only one string so it has to be handled only if referring bits have changed
                        if previousBits is None:
                            # any bit set?
                            if currentBits & bitMask:
                                printMessage = "set: "
                        else:
                            # any bit changed?
                            if (currentBits ^ previousBits) & bitMask:
                                if currentBits & bitMask:
                                    # any bit(s) are set (in case of multi-bit entries a change from e.g. 0x01 to 0x02 or from 0x03 to 0x01 will also show a set)
                                    printMessage = "set: "
                                else:
                                    # bit(s) has/have been cleared
                                    printMessage = "cleared: "
                        if printMessage:
                            printMessage += stateDict[bitMask]["message"]
                        # in case of single string but multi-bit mask print the current value, too
                        if Supporter.countSetBits(bitMask) > 1:
                            printMessage += f" [0x{currentBits:X}]"
                    elif type(stateDict[bitMask]["message"]) == list:
                        # multiple strings means the entry has to be handled in any case
                        leastNotZero = Supporter.leastNotZeroBit(bitMask)           # needed for shifting

                        # ensure state dict is correctly filled!
                        if len(stateDict[bitMask]["message"]) < (bitMask >> leastNotZero):
                            raise Exception(f"\"message\" element is list but contains too less entries, {bitMask >> leastNotZero} would be needed but there are only {len(stateDict[bitMask]['message'])}")

                        messageIndex = (currentBits & bitMask) >> leastNotZero      # calculate message index from current bits states (e.g. 0x0003 << 5 -> 0x0003)
                        printMessage = stateDict[bitMask]["message"][messageIndex]
                    if printMessage:
                        self.logger.message(stateDict[bitMask]["type"], self, printMessage)
                        if stateDict[bitMask]["type"] in ["critical", "fatal"]:
                            raise Exception(f"Meanwell device showed error or type {stateDict[bitMask]['type']}")
                            

        # handle all existing state information
        for stateName in self.STATUS_ELEMENTS.keys():
            valueName = self.CAN_COMMANDS[stateName]["valueName"]
            if valueName in chargingData:
                if len(chargingData[valueName]):
                    if (previousData is None) or (valueName not in previousData):
                        # element not contained in previous data so the whole entry is new
                        Supporter.debugPrint(f"{self.STATUS_ELEMENTS[stateName]}, {chargingData[valueName]}", color = "RED", borderSize = 0)
                        handleStateBits(self.STATUS_ELEMENTS[stateName], int(chargingData[valueName], 16))
                    elif chargingData[valueName] != previousData[valueName]:
                        # element in previous and current data but content has changed
                        handleStateBits(self.STATUS_ELEMENTS[stateName], int(chargingData[valueName], 16), int(previousData[valueName], 16))
                else:
                    raise Exception(f"got invalid chargingData, it contains key valueName but value is empty")
            else:
                #raise Exception(f"got invalid charging data dictionary, missing {valueName} entry")
                pass

        # handle some certain states
        if int(chargingData[self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.FAULT_STATUS]["valueName"]], 16) & (0x0001 <<  6):
            chargingData["operation state"] = "ON"
        else:
            chargingData["operation state"] = "OFF"

        return chargingData


    def threadInitMethod(self):
        self.homeAutomationValues = {}
        self.homeAutomationUnits = {}
        self.homeAutomationTopic = None     # discovery has still to be done
        self.SUPPORTED_COMMANDS = set()
        commands = [member for member in self.CAN_COMMAND_NAMES]
        for command in commands:
            self.SUPPORTED_COMMANDS.add(MeanWellNPB._cutTrailingDigits(command))              # get all commands, cut trailing digits and add it to a set so that all commands are unique, i.e. there will be one SERIAL even if there is a SERIAL1 and SERIAL2
            if not self.CAN_COMMANDS[command]["valueName"] in self.homeAutomationValues:      # each parameter gets initialized once, i.e. only one out of e.g. SERIAL1 and SERIAL2 will be handled here! 
                self.homeAutomationValues[self.CAN_COMMANDS[command]["valueName"]] = ""
                if self.CAN_COMMANDS[command]["unit"] is not None:
                    self.homeAutomationUnits[self.CAN_COMMANDS[command]["valueName"]] = self.CAN_COMMANDS[command]["unit"]

        self.chargingData = {}                        # will be filled with message content from Meanwell controller interface
        self.surplusPower = 0                         # surplus power received from power controller        
        self.surplusCurrent = 0                       # current calculated from received power and received accumulator voltage
        self.initialChargerValuesReceived = False     # to be set to True when the first messages with charger values from Meanwell charger arrived
        self.surplusCurrentUpdate = True              # to be set to True each time a message from power controller arrived with different surplus power value

        # subscribe to power controller that tells us what amount of power is available for Meanwell charger        
        self.mqttSubscribeTopic(self.createOutTopicFilter(self.createProjectTopic(self.configuration["powerController"])), globalSubscription = False)

        # test state handling
        if MeanWellNPB.TEST_STATE_HANDLING:
            previousValue = "0x0000"
            faultState = self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.FAULT_STATUS]["valueName"]
            testEntry  = self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.CURVE_CFG]["valueName"]
            for bit in range(1 << 8 - 1):
                self.logger.info(self, f"test run {bit} = 0x{bit:04X}")
                currentValue = f"0x{1 << bit:04X}"
                dummy = self._preProcessChargingData({testEntry : currentValue, faultState : "0"}, {testEntry : previousValue, faultState : "0"})
                previousValue = currentValue
            raise Exception(f"state handling tests finished, please check the logger outputs if necessary")


    def threadMethod(self):
        '''
        '''
        # read messages from project (not from Meanwell interface!)
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            Supporter.debugPrint(f"RXqueue", color = "RED", borderSize = 0)

            if self.configuration["powerControllerValue"] in newMqttMessageDict["content"]:
                if self.surplusPower != newMqttMessageDict["content"][self.configuration["powerControllerValue"]]:
                    self.surplusPower = newMqttMessageDict["content"][self.configuration["powerControllerValue"]]
                    self.chargingData["surplusPower"] = self.surplusPower
                    self.surplusCurrentUpdate = True    # different surplus power received, so an update is necessary

        # read message from Meanwell interface
        while not self.meanWellInterfaceQueue.empty():
            chargingDataMessageDict = self.readMqttQueue(mqttQueue = self.meanWellInterfaceQueue, error = False)
            newChargingData = chargingDataMessageDict["content"]
            
            # pre-processing charging data 
            newChargingData["surplusPower"] = self.surplusPower                 # not part of charger message so we have to add that value

            newChargingData = self._preProcessChargingData(newChargingData, self.chargingData)

            Supporter.debugPrint(f"Interface queue", color = "RED", borderSize = 0)

            if newChargingData != self.chargingData:
                Supporter.debugPrint(f"new charging data detected", color = "RED", borderSize = 0)
                self.chargingData = newChargingData
                self.initialChargerValuesReceived = True    # remember that charger values from Meanwell charger arrived, this is important since we cannot calculate correct current before we know the accumulator voltage

        # do we have to sent a message to the Meanwell charger with updated surplus current value?
        # - first it's checked if output voltage is OK, if that's not the case the output voltage will be set correctly, by clearing only self.initialChargerValuesReceived again the readback of the set value will initiate another turn where the output current can be set if output voltage is OK now
        # - if the output voltage was already OK just the output current is set
        #   - in case the output current is less than 5.0A the charger is switched OFF if it is not already OFF since an output current of less than 5.0A is not supported by the charger
        if self.surplusCurrentUpdate and self.initialChargerValuesReceived:
            Supporter.debugPrint(f"try to set current", color = "RED", borderSize = 0)
            if self.chargingData[self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.VOUT_SET]["valueName"]] != self.configuration["voltageOut"]:
                Supporter.debugPrint(f"ignore current but set voltage instead", color = "RED", borderSize = 0)
                voltageOut = self.configuration["voltageOut"]
                voltageOut = int(voltageOut * pow(10, self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.VOUT_SET]["resolution"]))
                self._transmitCommand(command = self.CAN_COMMAND_NAMES.VOUT_SET, address = self.configuration["address"], data = f"{voltageOut:04X}")         # set calculated output voltage
                self.initialChargerValuesReceived = False       # clear it again since the initial charger values contained invalid voltage value, wait until it has been updated, then try to set new current again
            else:
                # send message with new current to Meanwell charger
                surplusCurrent = self._calculateSurplusCurrent(self.chargingData["surplusPower"], self.chargingData[self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.VOUT_SET]["valueName"]]) # VOUT_SET is OK here since we need the voltage to calculate to current from given power!
                Supporter.debugPrint(f"voltage ok, now set current to {surplusCurrent}", color = "RED", borderSize = 0)
                surplusCurrent = int(surplusCurrent * pow(10, self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.IOUT_SET]["resolution"]))
                if surplusCurrent > 0:
                    self._transmitCommand(command = self.CAN_COMMAND_NAMES.IOUT_SET, address = self.configuration["address"], data = f"{surplusCurrent:04X}")     # set calculated current
                    if self.chargingData[self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.OPERATION]["valueName"]] == 0:
                        self._transmitCommand(command = self.CAN_COMMAND_NAMES.OPERATION, address = self.configuration["address"], data = "01")                   # switch charger ON if necessary
                else:
                    # since Meanwell chargers don't support currents less than 5.0A the charger has to be switched OFF instead
                    if self.chargingData[self.CAN_COMMANDS[self.CAN_COMMAND_NAMES.OPERATION]["valueName"]] == 1:
                        self._transmitCommand(command = self.CAN_COMMAND_NAMES.OPERATION, address = self.configuration["address"], data = "00")                   # switch charger OFF if necessary
                self.surplusCurrentUpdate = False       # update sent, but don't change the current stored in charger structure since we will get this by the next message from the Meanwell charger

        # do we have to update home automation values?
        if self.homeAutomationValues != self.chargingData:
            self.homeAutomationValues = dict(self.chargingData)     # do a real copy of the charging data dict (not just "a = b"!), since otherwise self.homeAutomationValues and self.chargingData cannot be compared
            if self.homeAutomationTopic is None:
                # first update so we have to discover the sensors as well
                self.homeAutomationTopic = self.homeAutomation.mqttDiscoverySensor(self.homeAutomationValues, unitDict = self.homeAutomationUnits, subTopic = "homeautomation")

            # finally publish contents, after sensors have been discovered
            self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True)


        # some code to test surplus power handling, will publish message as PowerPlant that is received by our queue handler
        if MeanWellNPB.TEST_SURPLUS_HANDLING:
            if self.initialChargerValuesReceived:
                if self.timer(name = "simulatePowerControl", timeout = 20, autoReset = True):
                    SURPLUS_TEST_AMPERES = [0,
                                            self.configuration["currentOutMin"] - 1.0,
                                            self.configuration["currentOutMin"],
                                            self.configuration["currentOutMin"] + 1.0,
                                            self.configuration["currentOutMin"] + 2.2,
                                            self.configuration["currentOutMin"] + 4.5,
                                            self.configuration["currentOutMax"],
                                            self.configuration["currentOutMax"] + 0.1,
                                            self.configuration["currentOutMax"] + 5.0,
                                            0]
                    counterValue = self.counter(name = "simulatePowerControl", value = len(SURPLUS_TEST_AMPERES), getValue = True, autoReset = True)
                    SURPLUS_VOLTAGE = self.configuration["voltageOut"]
                    SURPLUS_TEST_VALUE = SURPLUS_TEST_AMPERES[counterValue] * SURPLUS_VOLTAGE
                    OUT_TOPIC = self.createOutTopic(self.createProjectTopic(self.configuration["powerController"]))
                    POWER_DICT = {self.configuration["powerControllerValue"] : SURPLUS_TEST_VALUE}

                    Supporter.debugPrint([f"test value is {SURPLUS_TEST_VALUE} Watt = {SURPLUS_TEST_AMPERES[counterValue]} Amperes * {SURPLUS_VOLTAGE} Volts", f"out topic: {OUT_TOPIC}, surplus dict: {POWER_DICT}"], color = "RED")

                    self.mqttPublish(OUT_TOPIC, POWER_DICT, globalPublish = False, enableEcho = True)    # echo needed here since we "fake" a message to ourselves

                    if self.counter(name = "simulatePowerControlStopCounter", value = len(SURPLUS_TEST_AMPERES) + 1):
                        raise Exception(f"surplus handling tests finished")

