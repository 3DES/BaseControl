from Base.InterfaceBase import InterfaceBase
import time
from GridLoad.SocMeter import SocMeter
import serial
from Interface.Uart.Jbd.jbd import JBD

class Jbd485Interface(InterfaceBase):
    '''
    classdocs
    '''
    
    maxInitTries = 10

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Tmin": -40.0, "Tmax": -40.0, "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "Power":0.0,"toggleIfMsgSeen":False, "FullChargeRequired":False, "BmsEntladeFreigabe":False}

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "battCount"])
        self.tagsIncluded(["baudrate"], optional = True, default = 9600)
        #self.tries = 0
        #while self.tries <= self.maxInitTries:
        #    self.tries += 1
        #    try:
        #        
        #        self.p = PylontechStack(self.configuration["interface"], baud=self.configuration["baudrate"], manualBattcountLimit=self.configuration["battCount"])
        #        break
        #    except:
        #        time.sleep(10)
        #        self.logger.info(self, f"Device --{self.name}-- {self.tries} from {self.maxInitTries} inits failed.")
        #       if self.tries >= self.maxInitTries:
        #           raise Exception(f'{self.name} connection could not established! Check interface, baudrate, battCount!')

        self.serialConn = serial.Serial(
            port         = self.configuration["interface"],
            baudrate     = self.configuration["baudrate"],
        )
        self.jbd = JBD(self.serialConn)


    def threadMethod(self):
        print(self.jbd.readBasicInfo())
        print(self.jbd.readCellInfo())
        print(self.jbd.readDeviceInfo())


    def threadBreak(self):
        time.sleep(1.5)