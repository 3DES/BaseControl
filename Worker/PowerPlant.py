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
        '''
        Register topics here
        '''
        self.mqttSubscribeTopic("WatchDog/#")


    def threadMethod(self):
        self.logger.trace(self, "I am the PowerPlant thread = " + self.name)
        time.sleep(0.1)

        if Supporter.counter("unsubscribe", 20, singularTrue = True):
            self.mqttUnSubscribeTopic("WatchDog/#")
            
