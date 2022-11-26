import time
import serial


from Base.InterfaceBase import InterfaceBase


class UartInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        #self.tagsIncluded(["interface", "parity", "stopbits"])
        #self.tagsIncluded(["baudrate", "bytesize"], intIfy = True)
        #self.tagsIncluded(["timeout"], optional = True, default = None)
        #self.tagsIncluded(["xonxoff"], optional = True, default = 0)
        #self.tagsIncluded(["rtscts"], optional = True, default = 0)
        #self.serialConn = serial.Serial(
        #    port = self.configuration["interface"],
        #    baudrate = self.configuration["baudrate"],
        #    bytesize = self.configuration["bytesize"],
        #    parity = self.configuration["parity"],
        #    stopbits = self.configuration["stopbits"],
        #    timeout = self.configuration["timeout"],
        #    xonxoff = self.configuration["xonxoff"],
        #    rtscts = self.configuration["rtscts"],
        #    )


    #def threadInitMethod(self):
    #    pass


    def threadMethod(self):
        pass


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

