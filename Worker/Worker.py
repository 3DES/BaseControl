import time
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class Worker(ThreadObject):
    '''
    classdocs
    '''


    __instantiated_always_use_getters_and_setters = False    # Worker is a singleton!


    @classmethod
    def setup_instantiated(cls):
        '''
        Setter for cls.instantiated
        '''
        with cls.get_threadLock():
            if not Worker._Worker__instantiated_always_use_getters_and_setters:
                Worker._Worker__instantiated_always_use_getters_and_setters = True        # remember __init__ has been called now
            else:
                raise Exception("Worker already instantiated, no further instances allowed")


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        self.setup_instantiated()
        super().__init__(threadName, configuration)
        self.logger.info(self, "init (Worker)")


    def threadInitMethod(self):
        '''
        Register needed topics here
        '''
        #self.mqttSubscribeTopic("WatchDog/#")
        pass


    def threadMethod(self):
        #MqttBase.simulateExcepitonError(self.name, 5)
        pass

