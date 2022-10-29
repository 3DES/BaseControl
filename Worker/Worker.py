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
                raise Exception("Worker already instantiated, no further instances allowed")    # self.raiseException


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        self.setup_instantiated()
        super().__init__(threadName, configuration, logger)
        self.logger.info(self, "init (Worker)")


    def threadMethod(self):
        self.logger.trace(self, "I am the Worker thread = " + self.name)
        time.sleep(1)
        #MqttInterface.simulateExcepitonError(self.name, 5)

