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

        time.sleep(0.1)

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))

