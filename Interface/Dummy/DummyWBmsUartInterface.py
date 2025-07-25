
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
        self.HmaxVal = 3.7
        self.LmaxVal = 3.5
        
        self.LminVal = 3.2
        self.HminVal = 3.4

    def threadInitMethod(self):
        #self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Ladephase": "none", "Current":0.0, "Prozent":51, "toggleIfMsgSeen":False, "FullChargeRequired":False, "BmsEntladeFreigabe":True, "BmsLadeFreigabe":True}
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Ladephase": "none", "Current":0.0, "Prozent":51, "CurrentList":[3, 6, 15, -10], "VoltageList":[3.33,3.22,3.55,3.77], "toggleIfMsgSeen":False, "ChargeDischargeManagement":{"FullChargeRequired":False}, "BmsEntladeFreigabe":True}


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            try:
                newMqttMessageDict["content"] = self.extendedJson.parse(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                self.logger.error(self, f'Cannot convert {newMqttMessageDict["content"]} to dict')

            self.logger.info(self, " received queue message :" + str(newMqttMessageDict))

        if self.timer(name = "timerSoc", timeout = 8):
            self.timer(name = "timerSoc", remove = True)
            if self.BmsWerte["Vmax"] == self.HmaxVal:
                self.BmsWerte["Vmax"] = self.LmaxVal
                self.BmsWerte["Vmin"] = self.LminVal
                self.BmsWerte["Current"] = 50
            else:
                self.BmsWerte["Vmax"] = self.HmaxVal
                self.BmsWerte["Vmin"] = self.HminVal
                self.BmsWerte["Current"] = 10
            if self.BmsWerte["toggleIfMsgSeen"]:
                self.BmsWerte["toggleIfMsgSeen"] = False
            else:
                self.BmsWerte["toggleIfMsgSeen"] = True
        
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)

        #if self.timer(name = "timerFullChargeRequiredTest", timeout = 40):
        #       self.BmsWerte["ChargeDischargeManagement"]["FullChargeRequired"] = True




    #def threadBreak(self):
    #    pass

    #def threadTearDownMethod(self):
    #    pass

