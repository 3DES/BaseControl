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
import colorama
import functools
from enum import Enum


import sys
import re


class KacoController(ThreadObject):
    '''
    '''
    class KACO_VALUE(Enum):
        STATE       = "State"            # S            # mandatory
        U1          = "DcVoltageMppt1"   # U1
        I1          = "DcCurrentMppt1"   # I1
        P1          = "DcPowerMppt1"     # P1
        U2          = "DcVoltageMppt2"   # U2
        I2          = "DcCurrentMppt2"   # I2
        P2          = "DcPowerMppt2"     # P2
        UN          = "AcVoltage"        # UN
        IN          = "AcCurrent"        # IN
        UN1         = "AcVoltageL1"      # UN1
        IN1         = "AcCurrentL1"      # IN1
        UN2         = "AcVoltageL2"      # UN2
        IN2         = "AcCurrentL2"      # IN2
        UN3         = "AcVoltageL3"      # UN3
        IN3         = "AcCurrentL3"      # IN3
        POWER       = "DcPower"          # P
        PN          = "AcPower"          # PN           # mandatory
        COS         = "CosPhi"           # COS
        TEMPERATURE = "Temperature"      # T            # mandatory
        ENERGY      = "DailyEnergy"      # E            # mandatory
        TYPE        = "InverterType"     # WR           # mandatory

    KACO_VALUE_CONTEXT = {
        KACO_VALUE.STATE.value       : {"unit" : None, "variance" : None, "ignoreDelta": None},
        KACO_VALUE.U1.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.I1.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.P1.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.U2.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.I2.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.P2.value          : {"unit" : None, "variance" :  5.0, "ignoreDelta": None},
        KACO_VALUE.UN.value          : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.IN.value          : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.UN1.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.IN1.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.UN2.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.IN2.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.UN3.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.IN3.value         : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.POWER.value       : {"unit" : None, "variance" : 10.0, "ignoreDelta": None},
        KACO_VALUE.PN.value          : {"unit" : None, "variance" : 10.0, "ignoreDelta": None},
        KACO_VALUE.COS.value         : {"unit" : None, "variance" : None, "ignoreDelta": None},
        KACO_VALUE.TEMPERATURE.value : {"unit" : None, "variance" :  1.0, "ignoreDelta": None},
        KACO_VALUE.ENERGY.value      : {"unit" : "Wh", "variance" : 10.0, "ignoreDelta": None},
        KACO_VALUE.TYPE.value        : {"unit" : None, "variance" : None, "ignoreDelta": None},
    }


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        # for easier interface message handling use an extra queue
        self.kacoInterfaceQueue = Queue()
        
        # all messages published by our interfaces will be sent to our one interface queue
        super().__init__(threadName, configuration, {None : self.kacoInterfaceQueue})


    def threadInitMethod(self):
        self.kacoData = {}
        self.homeAutomationUnits = {}               # needed if units have to be given explicitly for certain data elements

        # fill all defined units into home automation units dict
        for member in self.KACO_VALUE_CONTEXT.keys():
            if self.KACO_VALUE_CONTEXT[member]["unit"] is not None:
                self.homeAutomationUnits[member] = self.KACO_VALUE_CONTEXT[member]["unit"]
        self.homeAutomationTopic = {}               # we need a topic for each slave found by our interface


    def compareHomeAutomation(self, publishedData : dict, newData : dict, force : bool = False):
        publish = False
        
        if force:
            publish = True
        else:
            # check all values contained in the dictionaries
            for entry in [member.value for member in self.KACO_VALUE]:
                if (entry not in publishedData) and (entry in newData):
                    publish = True  # new element has always to be published
                elif (entry in publishedData) and (entry in newData):
                    # do we have a defined ignore delta?
                    if self.KACO_VALUE_CONTEXT[entry]["ignoreDelta"] is not None:
                        minIgnoreDelta = self.KACO_VALUE_CONTEXT[entry]["ignoreDelta"]
                    else:
                        minIgnoreDelta = 0.0

                    # if there is a defined variance do a range check
                    if self.KACO_VALUE_CONTEXT[entry]["variance"] is not None:
                        publish = Supporter.deltaOutsideRange(newData[entry], publishedData[entry], dynamic = True, percent = self.KACO_VALUE_CONTEXT[entry]["variance"], minIgnoreDelta = minIgnoreDelta)
                    else:
                        # no variance means check if not equal
                        publish = newData[entry] != publishedData[entry]

                # first difference to be published found means stop searching
                if publish:
                    break
                    
        return publish


    def receiveKacoControllerMessage(self):
        '''
        Takes the lastly received bytes from easy meter, adds it to current receive buffer and tries to find a valid message
        If a valid message could be found it will be processed and proper values will be set
        '''
        # any message from our interface?
        while not self.kacoInterfaceQueue.empty():
            messageDict = self.readMqttQueue(mqttQueue = self.kacoInterfaceQueue, error = False)

            # take data out of messageDict from easy meter interface
            data = messageDict["content"]

            #Supporter.debugPrint(f"KACO thread received data = {data}")

            if "slave" in data:
                slave = data["slave"]
                if (slave not in self.kacoData) or (self.kacoData[slave] != data) or self.compareHomeAutomation(self.kacoData[slave], data):
                    self.kacoData[slave] = data     # remember received data
                    
                    if slave not in self.homeAutomationTopic:
                        self.homeAutomationTopic[slave] = self.homeAutomation.mqttDiscoverySensor(self.kacoData[slave], unitDict = self.homeAutomationUnits, subTopic = "homeautomation", senderName = slave)
                        #Supporter.debugPrint(f"homeautomation discovered: {slave}", color = "RED")

                    #Supporter.debugPrint(f"homeautomation: {self.kacoData[slave]}")

                    # finally publish contents, after sensors have been discovered
                    self.mqttPublish(self.homeAutomationTopic[slave], self.kacoData[slave], globalPublish = True)
            else:
                raise Exception(f"invalid message from interface received, \"slave\" element missed")


    def threadMethod(self):
        '''
        '''
        # read messages from project (not from EasyMeterInterface!!!)
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))

        # any Kaco controller data to be received?
        self.receiveKacoControllerMessage()


    def threadBreak(self):
        time.sleep(1)          # give other threads a chance to run and ensure that a thread which writes to the logger doesn't flood it


