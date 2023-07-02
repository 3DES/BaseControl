import json
import time
from Base.ThreadObject import ThreadObject


class BasicUsbRelais(ThreadObject):
    '''
    This class generates a {"cmd":"readRelayState"} and {"cmd":"readInputState"} msg all 60s and publishes it to the interface
    This class forwards all msg globally from interface

    Messages:
    {"cmd":"..."} will be forwarded to the interface
    {"cmd":"triggerWdRelay"} check if sender is the triggerThread and forward to the interface with "cmd":"triggerWd"
    {"gpio":{"relWr": "0", "relPvAus": "1", "relNetzAus": "0"}} will be mapped to {"setRelay":{"Relay0": "0", "Relay1": "1", "Relay5": "0", "Relay2": "1"}} and sent to the interface
    '''
    gpioCmd = "gpio"

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["triggerThread"], optional = True, default = "noTriggerThreadDefined")
        self.tagsIncluded(["relMapping"], optional = True, default = {})
        self.tagsIncluded(["gpioHandler"], optional = True, default = [])


    def threadInitMethod(self):
        self.mqttPublish(self.interfaceInTopics[0], "readRelayState", globalPublish = False, enableEcho = False)
        self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(self.configuration["triggerThread"]), self.MQTT_SUBTOPIC.TRIGGER_WATCHDOG), globalSubscription = False)
        for gpioHandler in self.configuration["gpioHandler"]:
            self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(gpioHandler)), globalSubscription = False)

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
                #todo evtl ausgelesenen wert mit localen vergleichen und nur dann weiterschicken
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                if not "triggerWd" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"], globalPublish = True, enableEcho = False)
            else:
                # We assume that cmd or self.name is a key in this dict. Other keys will raise a key error. 
                if "cmd" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["cmd"] == "triggerWdRelay":
                        if self.configuration["triggerThread"] in newMqttMessageDict["topic"]:
                            # This is a special msg. Watchdog will be only triggered if the sender thread is accepted. We convert the Msg to prevent that a thread can trigger interface directly.
                            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"triggerWd"}, globalPublish = False, enableEcho = False)
                        else:
                            # We got a watchdog trigger msg from a not authorised thread
                            raise Exception(f'Not authourised thread wants to trigger watchdog! Check usbRelais parameter -triggerThread- and watchdogName from topic {newMqttMessageDict["topic"]}. Current accepted thread is {self.configuration["triggerThread"]}')
                    else:
                        self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                else:
                    if self.gpioCmd in newMqttMessageDict["content"]:
                        found = False
                        tempRelais = {}
                        for key in list(self.configuration["relMapping"].keys()):
                            if key in newMqttMessageDict["content"][self.gpioCmd]:
                                found = True
                                if type(self.configuration["relMapping"][key]) == list:
                                    for relais in self.configuration["relMapping"][key]:
                                        tempRelais.update({relais:newMqttMessageDict["content"][self.gpioCmd][key]})
                                else:
                                    tempRelais.update({self.configuration["relMapping"][key]:newMqttMessageDict["content"][self.gpioCmd][key]})
                        if found:
                            self.mqttPublish(self.interfaceInTopics[0], {"setRelay":tempRelais}, globalPublish = False, enableEcho = False)

        if self.timer(name = "timerStateReq", timeout = 60):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readRelayState"}, globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readInputState"}, globalPublish = False, enableEcho = False)

        # Watchdog Test every max 100h, we do it all 4d
        if self.timer(name = "timerTestWd", timeout = 4*24*60*60):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"testWdRelay"}, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(0.1)