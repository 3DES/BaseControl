
import json
from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter


class DummySocMeterUartInterface(InterfaceBase):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

    def threadInitMethod(self):
        self.SocMonitorWerte = {"Ah":-1, "Current":0, "Prozent":50}


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                self.logger.error(self, f'Cannot convert {newMqttMessageDict["content"]} to dict')

            self.logger.info(self, " received queue message :" + str(newMqttMessageDict))

        if self.timer(name = "timerSoc", timeout = 10):
            self.timer(name = "timerSoc", remove = True)
            if self.SocMonitorWerte["Ah"] == 50:
                self.SocMonitorWerte["Ah"] = 30
            else:
                self.SocMonitorWerte["Ah"] = 50
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = False, enableEcho = False)

    #def threadBreak(self):
    #    pass

    #def threadTearDownMethod(self):
    #    pass

