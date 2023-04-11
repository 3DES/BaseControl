import json
import time
from Base.ThreadObject import ThreadObject


class UsbRelais(ThreadObject):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)


    def threadInitMethod(self):
        self.mqttPublish(self.interfaceInTopics[0], "readRelayState", globalPublish = False, enableEcho = False)
        #reset triggern
        #auslesen triggern
        pass

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            # check if we got a msg from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                #ausgelesenen wert mit localen vergleichen
                pass
            else:
                # We assume that cmd or self.name is a key in this dict. Other keys will raise a key error. 
                if "cmd" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["cmd"] == "triggerWdRelay" and "WatchDog" in newMqttMessageDict["topic"]:
                        # This is a special msg, it will be only forwarded from a thread called WatchDog
                        self.mqttPublish(self.interfaceInTopics[0], "triggerWdRelay", globalPublish = False, enableEcho = False)
                    else:
                        self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                else:
                    if self.name in newMqttMessageDict["content"]:
                        self.mqttPublish(self.interfaceInTopics[0], {"setRelay":newMqttMessageDict["content"][self.name]}, globalPublish = False, enableEcho = False)

        if self.timer(name = "timerStateReq", timeout = 3):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readRelayState"}, globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readInputState"}, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(0.1)