import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
import Base
import subprocess



class EasyMeter(Worker):
    '''
    classdocs
    '''
    #def threadInitMethod(self):
    #    pass


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))


            # @todo http://www.stefan-weigert.de/php_loader/sml.php


