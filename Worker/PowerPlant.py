import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
import Base
import subprocess
import json


class PowerPlant(Worker):
    '''
    classdocs
    '''
    def threadInitMethod(self):
        self.mqttSubscribeTopic(self.createInTopicFilter(self.getObjectTopic()), globalSubscription = True)


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

        ## @todo nur zum spielen...
        #if Supporter.counter("A", 10, autoReset = True):
        #    if Supporter.counter("B", 2, autoReset = True):
        #        self.logger.debug(self, "UNSUBSCRIBE")
        #        self.mqttUnSubscribeTopic("A/B/C")
        #    else:
        #        self.logger.debug(self, "SUBSCRIBE")
        #        self.mqttSubscribeTopic("A/B/C")


        if self.counter("C", 3, autoReset = True):
            #@todo den counter namespace nochmals pruefen, wo sind wir da genau?
            #@todo den timer noch fertig implementieren
            #self.mqttPublish(self.createInTopic(self.getObjectTopic()), "usually monologue is not possible", globalPublish = True)
            #self.mqttSendPackage(Base.MqttBase.MqttBase.MQTT_TYPE.PUBLISH, self.createInTopic(self.getObjectTopic()), "monologue is possible by sending message incocnito", incocnito = "IMustBeSomebodyElse")
            #self.mqttPublish(self.createInTopic(self.getObjectTopic()), "monologue is also possible by enabling echoing", globalPublish = True, enableEcho = True)
            pass

        if self.timer("T1", timeout = 60, firstTimeTrue = True):
            if not hasattr(self, "msgCtr"):
                self.msgCtr = 0 
            self.msgCtr += 1
            self.logger.info(self, f"TIMING EVENT T1 {self.msgCtr}")

        startTime = int(datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).timestamp())

        if self.timer("T2", timeout = 60, startTime = startTime):
            self.logger.info(self, "TIMING EVENT T2")

        #Supporter.memCheck()

