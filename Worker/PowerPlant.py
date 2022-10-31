import time
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter


class PowerPlant(Worker):
    '''
    classdocs
    '''
    def threadInitMethod(self):
        pass


    def threadMethod(self):
        self.logger.trace(self, "I am the PowerPlant thread = " + self.name)

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))


        # @todo nur zum spielen...
        if Supporter.counter("A", 10, autoReset = True):
            if Supporter.counter("B", 2, autoReset = True):
                self.logger.debug(self, "UNSUBSCRIBE")
                self.mqttUnSubscribeTopic("A/B/C")
            else:
                self.logger.debug(self, "SUBSCRIBE")
                self.mqttSubscribeTopic("A/B/C")


        if Supporter.counter("C", 3, autoReset = True):
            #@todo den counter namespace nochmals pruefen, wo sind wir da genau?
            #@todo den timer noch fertig implementieren
            self.mqttPublish(self.createInTopic(self.getObjectTopic()), "Selbstgespraech", globalPublish = True)

        if Supporter.timer("T", 3):
            self.logger.debug(self, "TIMEOUT")

