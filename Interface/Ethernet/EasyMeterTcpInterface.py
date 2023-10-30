from Interface.Ethernet.TcpInterface import TcpInterface
#import Interface.Ethernet.TcpInterface
import Base.Crc
from Base.Supporter import Supporter
from GridLoad.EasyMeter import EasyMeter
import colorama

import socket
import re


#class EasyMeterTcpInterface(Interface.Ethernet.TcpInterface.TcpInterface):
class EasyMeterTcpInterface(TcpInterface):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        if not self.tagsIncluded(["messageLength"], intIfy = True, optional = True):
            self.configuration["messageLength"] = 200     # default value if not given


    def threadInitMethod(self):
        super().threadInitMethod()      # we need the preparation from parental threadInitMethod 

        self.received = b""     # collect all received message parts here

        # patterns to match messages and values (the ^.*? will ensure that partial messages received at the beginning will be thrown away)
        self.SML_PATTERN = EasyMeter.getSmlPattern()
        #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), "", globalPublish = True)        # to clear retained message from mosquitto


    def readData(self):
        #EasyMeter.processBuffer(bytesArray)
        data = self.readSocket()
        if len(data):
            self.received += data               # add received data to receive buffer

            # full message received?
            if match := self.SML_PATTERN.search(self.received):
                bytesArray = bytearray(match.groups()[0])
                # log message
                #hexString = ":".join([ "{:02X}".format(char) for char in bytesArray])
                #self.logger.info(self, f"#{len(match.groups()[0])}: {hexString}")
    
                # remove message from receive buffer
                self.received = self.SML_PATTERN.sub(b"", self.received)

                #return bytesArray

            if len(self.received) > self.configuration["messageLength"]:
                self.logger.warning(self, f"cleared buffer because of buffer overflow prevention, length was {len(self.received)}")
                self.received = ""
           
        return ""


    #def threadMethod(self):
    #    pass


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

