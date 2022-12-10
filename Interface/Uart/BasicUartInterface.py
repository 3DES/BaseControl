import time
import serial    #pip install pyserial
import json
from Base.Supporter import Supporter

from Base.InterfaceBase import InterfaceBase


class BasicUartInterface(InterfaceBase):
    '''
    classdocs
    '''


    readData = b""


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
        success = True
        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            self.serialConn.close()
            self.serialConn.open()
        except Exception as exception:
            self.logger.error(self, f"Serial Port {self.name} reInit failed: {exception}")
            success = False
            # @todo perhaps wait a little bit
        return success


    def serialWrite(self, data):
        success = True
        try:
            self.serialConn.write(data)
        except Exception as exception:
            self.logger.error(self, f"Sending serial data failed: {exception}")
            success = False
        return success


    def serialReadLine(self):
        '''
        Reads data up to a new line
        don't mix serialRead() and serialReadLine()
        '''
        try:
            retVal = self.serialConn.readline()
        except:
            self.reInitSerial()
            retVal = b""
        return retVal


    def flush(self):
        '''
        Read serial once, then clear receive buffer
        '''
        self.serialReset_input_buffer()
        self.serialReset_output_buffer()

        if self.serialConn.inWaiting():
            self.serialConn.read(self.serialConn.inWaiting())

        self.readData = b""


    def serialRead(self, length : int = 0, timeout : int = 0):
        '''
        Reads data from serial until length bytes have been received or timeout has been reached
        
        @param length       amount of bytes to be received, 0 = read only once up to timeout, n = read until this amount of bytes have been received
        @param timeout      seconds to read from serial, 0 = use default timeout, n = read up to n seconds
        
        if not enough bytes have been received after timeout seconds an empty byte string will be returned! 
        don't mix serialRead() and serialReadLine()
        '''
        returnData = b""

        if timeout == 0:
            timeout = self.configuration["timeout"]

        if timeout:
            startTime = Supporter.getTimeStamp()
        try:
            while True:
                if self.serialConn.inWaiting():
                    receivedData = self.serialConn.read(self.serialConn.inWaiting())

                    if receivedData:
                        self.readData += receivedData

                # if length has been given check if length characters have been received
                if len(self.readData) >= length:
                    returnData = self.readData[:length]
                    self.readData = self.readData[length:]
                    self.logger.debug(self, f"OK")
                    break

                # if timeout has been given check if time is over
                if timeout and Supporter.getSecondsSince(startTime) > timeout:
                    self.logger.debug(self, f"timeout {len(self.readData)} {timeout}")
                    break
        except:
            self.reInitSerial()

        return returnData


    def serialReset_input_buffer(self):
        self.serialConn.reset_input_buffer()


    def serialReset_output_buffer(self):
        self.serialConn.reset_output_buffer()


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

