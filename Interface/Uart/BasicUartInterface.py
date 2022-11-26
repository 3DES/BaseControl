import time
import serial    #pip install pyserial
import json
from Base.Supporter import Supporter

from Base.InterfaceBase import InterfaceBase


class BasicUartInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.tagsIncluded(["interface"])
        self.tagsIncluded(["baudrate"], intIfy = True)

        self.tagsIncluded(["bytesize"], optional = True, default = serial.EIGHTBITS)
        self.tagsIncluded(["parity"], optional = True, default = serial.PARITY_NONE)
        self.tagsIncluded(["stopbits"], optional = True, default = serial.STOPBITS_ONE)
        self.tagsIncluded(["timeout"], optional = True, default = 4)
        self.tagsIncluded(["xonxoff"], optional = True, default = False)
        self.tagsIncluded(["rtscts"], optional = True, default = False)
        self.tagsIncluded(["writeTimeout"], optional = True, default = 4)


    def reInitSerial(self):
        error = False
        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            self.serialConn.close()
            self.serialConn.open()
        except Exception as exception:
            self.logger.error(self, f"Serial Port {self.name} reInit failed: {exception}")
            error = True
            # @todo perhaps wait a little bit
        return error


    def serialWrite(self, data):
        error = False
        try:
            self.serialConn.write(data)
        except Exception as exception:
            self.logger.error(self, f"Sending serial data failed: {exception}")
            error = True
        return error


    def serialReadLine(self):
        try:
            retVal = self.serialConn.readline()
        except:
            self.reInitSerial()
            retVal = b""
        return retVal


    def serialRead(self, length : int = 0, timeout : int = 0):
        returnData = b""

        if timeout:
            startTime = Supporter.getTimeStamp()
        try:
            while True:
                receivedData = self.serialConn.read()
                if receivedData:
                    returnData += receivedData

                    # if length has been given check if length characters have been received
                    if len(returnData) >= length:
                        break

                # if timeout has been given check if time is over
                if timeout and Supporter.getSecondsSince(startTime) > timeout:
                    break
        except:
            self.reInitSerial()

        return returnData


    def serialReset_input_buffer(self):
        self.serialConn.reset_input_buffer()


    def threadInitMethod(self):
        self.serialConn = serial.Serial(
            port         = self.configuration["interface"],
            baudrate     = self.configuration["baudrate"],
            bytesize     = self.configuration["bytesize"],
            parity       = self.configuration["parity"],
            stopbits     = self.configuration["stopbits"],
            timeout      = self.configuration["timeout"],
            xonxoff      = self.configuration["xonxoff"],
            writeTimeout = self.configuration["writeTimeout"],
            rtscts       = self.configuration["rtscts"]
        )


    #def threadMethod(self):


    #def threadBreak(self):
    #    pass


    def threadTearDownMethod(self):
        self.serialConn.close()

