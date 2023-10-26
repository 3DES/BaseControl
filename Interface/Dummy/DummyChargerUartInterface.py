import time


from Base.InterfaceBase import InterfaceBase


class DummyChargerUartInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)


    def threadInitMethod(self):
        self.chargerValues = {"PvVoltage":-1, "Current":0, "Power":500}


    def threadMethod(self):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = False, enableEcho = False)
        if self.chargerValues["Power"] == 500:
            self.chargerValues["Power"] = 20
        else:
            self.chargerValues["Power"] = 500

    def threadBreak(self):
        time.sleep(10)