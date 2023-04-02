
import json
from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter


class DummyWBmsUartInterface(InterfaceBase):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

    def threadInitMethod(self):
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Ladephase": "none", "Current":0.0, "Prozent":51, "toggleIfMsgSeen":False, "FullChargeRequired":False, "BmsEntladeFreigabe":True}


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
            if self.BmsWerte["Vmax"] == 4.0:
                self.BmsWerte["Vmax"] = 3.0
                self.BmsWerte["Current"] = 50
            else:
                self.BmsWerte["Vmax"] = 4.0
                self.BmsWerte["Current"] = 10
            if self.BmsWerte["toggleIfMsgSeen"]:
                self.BmsWerte["toggleIfMsgSeen"] = False
            else:
                self.BmsWerte["toggleIfMsgSeen"] = True
        
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)

        #if self.timer(name = "timerFullChargeRequiredTest", timeout = 40):
        #       self.BmsWerte["FullChargeRequired"] = True




    #def threadBreak(self):
    #    pass

    #def threadTearDownMethod(self):
    #    pass

