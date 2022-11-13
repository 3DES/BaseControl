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


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        self.easyMeterInterfaceQueue = Queue()  
        super().__init__(threadName, configuration, [self.easyMeterInterfaceQueue])

        # check and prepare mandatory parameters
        self.tagsIncluded(["loadCycle", "gridLossThreshold", "conservativeDelta", "progressiveDelta", "messageInterval"], intIfy = True)


        if (self.configuration["loadCycle"] // self.configuration["messageInterval"]) <= 1:
            raise Exception(f"loadCycle must to be larger than messageInterval") 
            
        if ((self.configuration["loadCycle"] // self.configuration["messageInterval"]) * self.configuration["messageInterval"]) != self.configuration["loadCycle"]:  
            raise Exception(f"loadCycle has to be an integer multiple of messageInterval") 

        if self.configuration["loadCycle"] <= (3 * self.configuration["gridLossThreshold"]):
            raise Exception(f"loadCycle has to be at least 4 times gridLossThresold") 
        
        if self.configuration["gridLossThreshold"] <= 0:
            raise Exception(f"gridLossThresold must be larger than 0") 
    
    
    #def threadInitMethod(self):
    #    pass


    def threadInitMethod(self):
        self.received = b""     # collect all received message parts here

        # patterns to match messages and values
        self.smlPattern = re.compile(b"^.*?(\x1b{4}\x01{4}.*?\x1b{4}.{4})", re.MULTILINE | re.DOTALL)
        self.smlValues = {
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
        self.deliveredEnergyKey = "2.8.0"

        self.energyValueNames = {
            # to be used as indices for self.energyValues[]
            "backedupEnergyLevel" : 0,      # the energy value one before the last one has been calculated (so we can calculate two deltas, the current one and the previous one)
            "lastSentEnergyValue" : 1,      # energy value when last delta has been calculated
            "currentEnergyLevel"  : 2,      # filled with every received grid meter message
        }
        self.energyValues             = [0, 0, 0]       # remember last three energy values, two times "loadCycle" ago, "loadCycle" ago and now
        self.lastEasyMeterMessageTime = 0               # timestamp of the last valid message received from easy meter (not from the thread EasyMeter!!!)
        self.gridLossDetected         = True            # grid loss detected in current cycle, first cycle after power up will always be a grid loss one
        
        # data from easy meter message
        self.energyData = {
            "invalidMessages"     : 0,      # we need an init value here, otherwise "+= 1" will fail!
            "lastInvalidMessage"  : 0,      # time last invalid message has been detected
            "invalidMessageError" : 0,      # reason why the last message has been detected as invalid, e.g. "invalid CRC", "value not found", "value found twice"
            "allowedPower"        : 0,      # currently allowed power to be taken from the grid to load the batteries (inverter thread has to calculate proper current with known battery voltage)
            "previousPower"       : 0,      # previous allowed power, for logging
            "previousReduction"   : 0,      # reduction used for previous power level (has already been subtracted!)
            "currentReduction"    : 0,      # reduction used for currently allowed power level (has already been subtracted from allowedPoer!)
            "updatePowerValue"    : False,  # set to True in the one message every "loadCycle" seconds to inform the worker thread that an update should be done now 
        }            


    def receiveGridMeterMessage(self):
        '''
        Takes the lastly received bytes from easy meter, adds it to current receive buffer and tries to find a valid message
        If a valid message could be found it will be processed and proper values will be set
        '''
        if not self.easyMeterInterfaceQueue.empty():
            invalidMessage = ""

            data = self.easyMeterInterfaceQueue.get(block = False)      # read a message from interface

            # last two bytes are the CRC so calculate CRC over the first n-2 bytes and compare result with CRC in the last two bytes
            if Base.Crc.Crc.crc16EasyMeter(data[:-2]) != Base.Crc.Crc.bytesToWordBigEndian(data[-2:]):
                invalidMessage = "invalid CRC"
            else:
                for key in self.smlValues:
                    matcher = self.smlValues[key]["regex"]
                    match = matcher.findall(data)
                    hexString = ":".join([ "{:02X}".format(char) for char in data])
                    if not len(match):
                        self.logger.warning(self, f"no match for {key} in easy meter message: {hexString}")
                        invalidMessage = f"element for {key} not found"
                        break
                    elif len(match) > 1:
                        self.logger.warning(self, f"too many matches for {key} in easy meter message: {hexString}")
                        invalidMessage = f"element for {key} found {len(match)} times"
                        break
                    else:
                        value = str(int.from_bytes(match[0], byteorder = "big", signed = self.smlValues[key]["signed"]))
                        self.energyData[key] = value[:-self.smlValues[key]["resolution"]] + "." + value[-self.smlValues[key]["resolution"]:]  

            if not invalidMessage:
                self.logger.debug(self, str(self.energyData) + f" (left:{len(self.received)})")

                # no initial value (probably first message ever received), so use current one!
                if self.energyValues[self.energyValueNames["lastSentEnergyValue"]] == 0:
                    self.energyValues[self.energyValueNames["lastSentEnergyValue"]] = self.energyData[self.deliveredEnergyKey]

                # remember current energy value and current time
                self.energyValues[self.energyValueNames["currentEnergyLevel"]] = self.energyData[self.deliveredEnergyKey]
                self.lastEasyMeterMessageTime = Supporter.getTimeStamp()
            else:
                self.energyData["invalidMessages"]   += 1
                self.energyData["lastInvalidMessage"] = invalidMessage


    def prepareNewEasyMeterMessage(self):
        '''
        Should be called every "loadCycle" seconds (synchronized to quarter hours)
        
        Checks if grid loss has been detected and calculates new power value for the message to the worker thread
        '''
        # handle grid loss if necessary
        if not self.gridLossDetected:
            # grid is OK so send proper values
            lastEnergyDelta    = int(self.energyValues[self.energyValueNames["lastEnergyLevel"]]    - self.energyValues[self.energyValueNames["backedupEnergyLevel"]])
            currentEnergyDelta = int(self.energyValues[self.energyValueNames["currentEnergyLevel"]] - self.energyValues[self.energyValueNames["lastSentEnergyValue"]])
            reductionLevel     = self.configuration["conservativeDelta"] if lastEnergyDelta > currentEnergyDelta else self.configuration["progressiveDelta"]
            newPowerLevel      = currentEnergyDelta / (60*60 / self.configuration["loadCycle"]) - reductionLevel            # 1 hour / "loadCycle" to calculate power from energy!
        else:
            # grid loss handling
            reductionLevel     = self.configuration["conservativeDelta"]
            newPowerLevel      = 0

        # copy current values over to previous one
        self.energyData["previousPower"]     = self.energyData["allowedPower"]
        self.energyData["previousReduction"] = self.energyData["currentReduction"]

        # fill in new current values
        self.energyData["allowedPower"]     = newPowerLevel
        self.energyData["currentReduction"] = reductionLevel        # for logging and debugging only

        # set to True for this one message only if there have been any changes since last turn and the power difference is more than 10%
        self.energyData["updatePowerValue"] = (((self.energyData["allowedPower"] != self.energyData["previousPower"]) or
                                               (self.energyData["currentReduction"] != self.energyData["previousReduction"])) and 
                                               (Supporter.absolutePercentageDifference(self.energyData["allowedPower"], self.energyData["previousPower"]) > 10))

        # reset some values for next turn
        self.gridLossDetected = False                               # reset grid loss detection for next cycle
        self.lastEasyMeterMessageTime = Supporter.getTimeStamp()    # set last message time


    def threadMethod(self):
        '''
        first loop:
            self.gridLossDetected = True
       
        every loop run:
            "lastSentEnergyValue" == 0:
                fill in current energy level (overall first cycle is probably a "shorter" one but that doesn't matter)
            time since last time > 2 minutes -> error (probably grid loss):
                self.gridLossDetected = True

        every minute a message is sent out:
            containing all data, some data could be unchanged, others will be new

        every event time:
            self.gridLossDetected = False
            self.lastEasyMeterMessageTime = now
            store new power level
            send signal message (in case of real grid loss nth. will happen but in case it's a bug and there is no grid loss a message will be sent!

        1st cycle is a grid loss one
        2nd cycle is probably a shorter one (since timer is synchronized to quarter hours the 2nd cycle length depends on start time related to next quarter hour)
        3rd... cycles are common ones
        '''

        self.energyData["updatePowerValue"] = False     # set to False for all messages (except the one every "loadCycle" seconds)

        # read messages from project (not from EasyMeterInterface!!!)
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))

        # grid loss detected?
        if Supporter.getDeltaTime(self.lastEasyMeterMessageTime) > self.configuration["gridLossThreshold"]:
            self.gridLossDetected = True

        # any grid meter data to be received?
        self.receiveGridMeterMessage()

        # prepare the one message every "loadCycle" seconds that contains new power values
        if self.timer("energyLoadTimer", timeout = self.configuration["loadCycle"], startTime = Supporter.getTimeOfToday(), firstTimeTrue = True):         # start timer with the interval in which new load parameters have to be sent out, timer is synchronized to the real time and not to random time it has been started
            self.prepareNewEasyMeterMessage()


        # one message every 60 seconds
        if self.timer("messageTimer", timeout = 60, startTime = Supporter.getTimeOfToday(), firstTimeTrue = False):
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.energyData, globalPublish = False)

