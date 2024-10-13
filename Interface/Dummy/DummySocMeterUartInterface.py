
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
        self.cmdList = []


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            try:
                newMqttMessageDict["content"] = self.extendedJson.parse(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                self.logger.error(self, f'Cannot convert {newMqttMessageDict["content"]} to dict')


            if "Prozent" in newMqttMessageDict["content"]:
                self.cmdList.append("setSocToValue")
                self.cmdList.append(str(newMqttMessageDict["content"]["Prozent"]))
                self.SocMonitorWerte["Prozent"] = newMqttMessageDict["content"]["Prozent"]
            elif "cmd" in newMqttMessageDict["content"]:
                # If cmd is resetSoc we add a special cmd socResetMaxAndHold, else we add all cmd to cmdList {"cmd":["",""]} and {"cmd":""} is accepted
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    self.cmdList.append("socResetMaxAndHold")
                elif newMqttMessageDict["content"]["cmd"] == list:
                    self.cmdList += newMqttMessageDict["content"]["cmd"]
                else:
                    self.cmdList.append(newMqttMessageDict["content"])

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

