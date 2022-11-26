import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
import Base
import subprocess
import Base.Crc
from queue import Queue


import sys
import re


class EasyMeter(ThreadObject):
    '''
    classdocs
    
    http://www.stefan-weigert.de/php_loader/sml.php
    '''


    # patterns to match messages and values
    SML_VALUES = {
        # OBIS no.                                                                                                                            resolution = 1 -> 0.1, 2 -> 0.01, ... n -> 10^(-n)
        "1.8.0"  : { "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x00\xFF\x64\x00\x02\x80\x01\x62\x1E\x52\xFC\x59(.{8})\x01', re.MULTILINE | re.DOTALL), "resolution" : 4, "signed" : False, "description" : "positiveActiveEnergyTotal" },       # "Bezug total"
        "2.8.0"  : { "regex" : re.compile(b'\x77\x07\x01\x00\x02\x08\x00\xFF\x64\x00\x02\x80\x01\x62\x1E\x52\xFC\x59(.{8})\x01', re.MULTILINE | re.DOTALL), "resolution" : 4, "signed" : False, "description" : "negativeActiveEnergyTotal" },       # "Lieferung total"
        "1.8.1"  : { "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x01\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 4, "signed" : False, "description" : "positiveActiveEnergyT1"    },       # "Bezug Tarif1"
        "1.8.2"  : { "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x02\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 4, "signed" : False, "description" : "positiveActiveEnergyT2"    },       # "Bezug Tarif2"
        "16.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x10\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 2, "signed" : True,  "description" : "activeInstantaneousPower"  },       # "Momentanleistung gesammt, vorzeichenbehaftet"
        "36.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\\\x24\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',           re.MULTILINE | re.DOTALL), "resolution" : 2, "signed" : True,  "description" : "activeInstantaneousPowerL1"},       # "Momentanleistung L1, vorzeichenbehaftet"
        "56.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x38\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 2, "signed" : True,  "description" : "activeInstantaneousPowerL2"},       # "Momentanleistung L2, vorzeichenbehaftet"
        "76.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x4C\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 2, "signed" : True,  "description" : "activeInstantaneousPowerL3"},       # "Momentanleistung L3, vorzeichenbehaftet"
        "32.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x20\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 1, "signed" : False, "description" : "instantaneousVoltageL1"    },       # "aktuelle Spannung L1"
        "52.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x34\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 1, "signed" : False, "description" : "instantaneousVoltageL2"    },       # "aktuelle Spannung L2"
        "72.7.0" : { "regex" : re.compile(b'\x77\x07\x01\x00\x48\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',             re.MULTILINE | re.DOTALL), "resolution" : 1, "signed" : False, "description" : "instantaneousVoltageL3"    },       # "aktuelle Spannung L3"
    }
    DELIVERED_ENERGY_KEY = "2.8.0"

    SECONDS_PER_HOUR = 60 * 60      # an hour has 3600 seconds
    POWER_OFF_LEVEL  = 0            # 0 watts means power OFF


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        self.easyMeterInterfaceQueue = Queue()
        super().__init__(threadName, configuration, [self.easyMeterInterfaceQueue])


        # initialize object variables...
        # dictionary to hold process data that are used to decide if and how much power can be used to load the batteries
        self.energyProcessData = {
            "currentEnergyLevel"     : 0,
            "lastEnergyLevel"        : 0,
            "backedupEnergyLevel"    : 0,

            "currentEnergyTimestamp" : 0,

            "gridLossDetected"       : True,
        }

        # data for easy meter message to be sent out to worker thread
        self.energyData = {
            "invalidMessages"            : 0,      # we need an initial value here, otherwise "+= 1" will fail!
            "lastInvalidMessageTimeStamp": 0,      # time last invalid message has been detected
            "invalidMessageError"        : 0,      # reason why the last message has been detected as invalid, e.g. "invalid CRC", "value not found", "value found twice"

            "allowedPower"               : 0,      # allowed power to be taken from the grid to load the batteries (inverter thread has to calculate proper current with known battery voltage)
            "allowedReduction"           : 0,      # allowed reduction used for allowed power level (has already been subtracted from allowedPoer!)
            "allowedTimestamp"           : 0,      # time stamp when allowed power has been set for the first time

            "previousPower"              : 0,      # previous allowed power, for logging
            "previousReduction"          : 0,      # reduction used for previous power level (has already been subtracted!)
            "previousTimestamp"          : 0,      # time stamp when the previous power has been taken

            "updatePowerValue"           : False,  # set to True in the one message every "loadCycle" seconds to inform the worker thread that an update should be done now 
        }

        # check and prepare mandatory parameters
        self.tagsIncluded(["loadCycle", "gridLossThreshold", "conservativeDelta", "progressiveDelta", "minimumPowerStep"], intIfy = True)

        if not self.tagsIncluded(["messageInterval"], intIfy = True, optional = True):
            self.configuration["messageInterval"] = 60     # default value if not given

        if (self.configuration["loadCycle"] // self.configuration["messageInterval"]) <= 1:
            raise Exception(f"loadCycle must to be larger than messageInterval =={self.configuration['messageInterval']}") 

        if ((self.configuration["loadCycle"] // self.configuration["messageInterval"]) * self.configuration["messageInterval"]) != self.configuration["loadCycle"]:  
            raise Exception(f"loadCycle has to be an integer multiple of messageInterval")

        if self.configuration["loadCycle"] <= (4 * self.configuration["gridLossThreshold"]):
            raise Exception(f"loadCycle has to be at least 4 times gridLossThresold")

        if self.configuration["gridLossThreshold"] <= 0:
            raise Exception(f"gridLossThresold must be larger than 0 seconds")

        if self.configuration["minimumPowerStep"] < 100:
            raise Exception(f"minimumPowerStep must be at least 100 watts")


    #def threadInitMethod(self):
    #    pass


    def processReceivedMessage(self, data : str) -> str:
        '''
        Check and process a data message received from easy meter
        
        All received data will be filled into self.energyData
        '''
        messageError = ""

        # last two bytes are the CRC so calculate CRC over the first n-2 bytes and compare result with CRC in the last two bytes
        if Base.Crc.Crc.crc16EasyMeter(data[:-2]) != Base.Crc.Crc.bytesToWordBigEndian(data[-2:]):
            messageError = "invalid CRC"
        else:
            # try to match all keys since messages always have same content, it's an error if one key hasn't been found at all or has been found twice!
            hexString = ":".join([ "{:02X}".format(char) for char in data])     # create printable string for log message, for the case of an error
            for key in self.SML_VALUES:
                matcher = self.SML_VALUES[key]["regex"]
                match = matcher.findall(data)
                if not len(match):
                    self.logger.warning(self, f"no match for {key} in easy meter message: {hexString}")
                    messageError = f"element for {key} not found"
                    break
                elif len(match) > 1:
                    self.logger.warning(self, f"too many matches for {key} in easy meter message: {hexString}")
                    messageError = f"element for {key} found {len(match)} times"
                    break
                else:
                    value = str(int.from_bytes(match[0], byteorder = "big", signed = self.SML_VALUES[key]["signed"]))
                    self.energyData[key] = value[:-self.SML_VALUES[key]["resolution"]] + "." + value[-self.SML_VALUES[key]["resolution"]:]  
        return messageError


    def handleReceivedValues(self, messageError : bool):
        '''
        Check result from processed data and fill in proper values or store error information
        '''
        if not messageError:
            self.logger.debug(self, str(self.energyData))

            # current energy level == 0 means script has been (re-)started and we are here for the first time, in that case take the values received with the last message
            if self.energyProcessData["currentEnergyLevel"] == 0:              # can only happen after reboot since this is the real overall energy measured so far
                self.energyProcessData["backedupEnergyLevel"] = self.energyData[self.DELIVERED_ENERGY_KEY]
                self.energyProcessData["lastEnergyLevel"]     = self.energyData[self.DELIVERED_ENERGY_KEY]
            else:
                # backup last levels
                self.energyProcessData["backedupEnergyLevel"] = self.energyProcessData["lastEnergyLevel"]
                self.energyProcessData["lastEnergyLevel"]     = self.energyProcessData["currentEnergyLevel"]

            # remember current level and current time
            self.energyProcessData["currentEnergyLevel"]     = self.energyData[self.DELIVERED_ENERGY_KEY]
            self.energyProcessData["currentEnergyTimestamp"] = Supporter.getTimeStamp()
        else:
            # logging values only
            self.energyData["invalidMessages"]            += 1
            self.energyData["lastInvalidMessageTimeStamp"] = Supporter.getTimeStamp()
            self.energyData["invalidMessageError"]         = messageError


    def receiveGridMeterMessage(self):
        '''
        Takes the lastly received bytes from easy meter, adds it to current receive buffer and tries to find a valid message
        If a valid message could be found it will be processed and proper values will be set
        '''
        if not self.easyMeterInterfaceQueue.empty():
            while not self.easyMeterInterfaceQueue.empty():
                data = self.easyMeterInterfaceQueue.get(block = False)  # read a message from interface but take only last one (if there are more they can be thrown away, only the newest one is from interest)

            messageError = self.processReceivedMessage(data)            # fill variables from message content (if message is OK)
            self.handleReceivedValues(messageError)                     # process filled variables and try to calculate new power level


    def calculateNewPowerLevel(self):
        '''
        Calculate new power level from last and current energy values
        '''
        # handle grid loss if necessary, otherwise calculate new power levels
        if self.energyProcessData["gridLossDetected"]:
            # grid loss handling
            newReductionLevel  = self.configuration["conservativeDelta"]
            newPowerLevel      = self.POWER_OFF_LEVEL
        else:
            # grid is OK so send proper values
            lastEnergyDelta    = int(self.energyProcessData["lastEnergyLevel"]    - self.energyProcessData["backedupEnergyLevel"])
            currentEnergyDelta = int(self.energyProcessData["currentEnergyLevel"] - self.energyProcessData["lastEnergyLevel"])
            if lastEnergyDelta > currentEnergyDelta:
                newReductionLevel = self.configuration["conservativeDelta"]
            else:
                newReductionLevel = self.configuration["progressiveDelta"]
            newPowerLevel      = currentEnergyDelta / (self.SECONDS_PER_HOUR / self.configuration["loadCycle"]) - newReductionLevel            # 1 hour / "loadCycle" to calculate power from energy! This is ok even for the first cycle that can be a bit shorter since in that case less energy will be calculated than really collected

            # no negative power level but with reduction level this can happen!
            if newPowerLevel < self.POWER_OFF_LEVEL:
                newPowerLevel = self.POWER_OFF_LEVEL

        return (newPowerLevel, newReductionLevel)


    def prepareNewEasyMeterMessage(self):
        '''
        Should be called every "loadCycle" seconds (synchronized to quarter hours)

        Checks if grid loss has been detected and calculates new power value for the message to the worker thread
        '''
        # calculate new power level and reduction value
        (newPowerLevel, newReductionLevel) = self.calculateNewPowerLevel()

        # do we have to switch OFF -or- difference between current and last set power level large enough?
        messageTime = Supporter.getTimeStamp()
        if (newPowerLevel == self.POWER_OFF_LEVEL) or (Supporter.absoluteDifference(newPowerLevel, self.energyData["allowedPower"]) >= self.configuration["minimumPowerStep"]): 
            # copy current values over to previous ones
            self.energyData["previousPower"]     = self.energyData["allowedPower"]
            self.energyData["previousReduction"] = self.energyData["allowedReduction"]
            self.energyData["previousTimestamp"] = self.energyData["allowedTimestamp"]

            # fill in new current values
            self.energyData["allowedPower"]     = newPowerLevel
            self.energyData["allowedReduction"] = newReductionLevel
            self.energyData["allowedTimestamp"] = messageTime          # remember time of last set power level (since not every "loadCycle" a new level is set! 

            # tag this message as message with new power level
            self.energyData["updatePowerValue"] = True

        # set last message time
        self.energyProcessData["currentEnergyTimestamp"] = messageTime    

        # reset some values for next turn
        self.energyProcessData["gridLossDetected"] = False                               # reset grid loss detection for next cycle


    def threadMethod(self):
        '''
        first loop:
            self.energyProcessData["gridLossDetected"] = True
       
        every loop run:
            "lastEnergyLevel" == 0:
                fill in current energy level (overall first cycle is probably a "shorter" one but that doesn't matter)
            time since last time > 2 minutes -> error (probably grid loss):
                self.energyProcessData["gridLossDetected"] = True

        every minute a message is sent out:
            containing all data, some data could be unchanged, others will be new

        every event time:
            self.energyProcessData["gridLossDetected"] = False
            self.energyProcessData["currentEnergyTimestamp"] = now
            store new power level
            send signal message (in case of real grid loss nth. will happen but in case it's a bug and there is no grid loss a message will be sent!

        1st cycle is a grid loss one
        2nd cycle is probably a shorter one (since timer is synchronized to quarter hours the 2nd cycle length depends on start time related to next quarter hour)
        3rd... cycles are common ones
        '''

        # read messages from project (not from EasyMeterInterface!!!)
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))

        # grid loss detected?
        if Supporter.getSecondsSince(self.energyProcessData["currentEnergyTimestamp"]) > self.configuration["gridLossThreshold"]:
            self.energyProcessData["gridLossDetected"] = True

        # any grid meter data to be received?
        self.receiveGridMeterMessage()

        # prepare the one message every "loadCycle" seconds that contains new power values
        if self.timer("energyLoadTimer", timeout = self.configuration["loadCycle"], startTime = Supporter.getTimeOfToday(), firstTimeTrue = True):         # start timer with the interval in which new load parameters have to be sent out, timer is synchronized to the real time and not to random time it has been started
            self.prepareNewEasyMeterMessage()

        # one message every 60 seconds
        if self.timer("messageTimer", timeout = self.configuration["messageInterval"], startTime = Supporter.getTimeOfToday(), firstTimeTrue = False):
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.energyData, globalPublish = False)
            self.logger.info(self, "new message: " + str(self.energyData))
            self.energyData["updatePowerValue"] = False     # set to False (again) for all following messages until it has been decided to set a new power level

