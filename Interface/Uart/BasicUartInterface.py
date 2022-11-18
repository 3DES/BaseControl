import time
import serial    #pip install pyserial
import json

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


    def reInitSerial(self):
        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            self.serialConn.close()
            self.serialConn.open()
        except:
            self.logger.error(self, f"Serial Port {self.name} reInit failed!")
            # @todo perhaps wait a little bit

    def serialWrite(self, data):
        self.serialConn.write(data)

    def serialReadLine(self):
        try:
            retVal = self.serialConn.readline()
        except:
            self.reInitSerial()
            retVal = b""
        return retVal

    def serialRead(self):
        try:
            retVal = self.serialConn.read()
        except:
            self.reInitSerial()
            retVal = b""
        return retVal

    def serialReset_input_buffer(self):
        self.serialConn.reset_input_buffer()

    def threadInitMethod(self):
        self.serialConn = serial.Serial(
            port = self.configuration["interface"],
            baudrate = self.configuration["baudrate"],
            timeout = self.configuration["timeout"]
            )

        #self.serialConn = self.serial.Serial(self.configuration["interface"], self.configuration["baudrate"], timeout=4)

        #self.serialConn = serial.Serial(
        #    port = self.configuration["interface"],
        #    baudrate = self.configuration["baudrate"],
        #    bytesize = self.configuration["bytesize"],
        #    parity = self.configuration["parity"],
        #    stopbits = self.configuration["stopbits"],
        #    timeout = self.configuration["timeout"],
        #    xonxoff = self.configuration["xonxoff"],
        #    rtscts = self.configuration["rtscts"]
        #    )


    #def threadMethod(self):


    #def threadBreak(self):
    #    pass


    def threadTearDownMethod(self):
        self.serialConn.close()

