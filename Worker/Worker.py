import time
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class Worker(ThreadObject):
    '''
    classdocs
    '''


    instantiated = False    # Worker is a singleton!


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        if self.setInstantiated():
            super().__init__(threadName, configuration, logger)
            self.logger.info(self, "init (Worker)")
        else:
            self.raiseException("Worker already instantiated, no further instances allowed")


    @classmethod
    def setInstantiated(cls):
        '''
        Setter for cls.instantiated
        '''
        setupResult = False
        with cls.threadLock:
            if not cls.instantiated:
                cls.instantiated = True        # remember __init__ has been called now
                setupResult = True
        return setupResult


    def threadMethod(self):
        self.logger.trace(self, "I am the Worker thread")
        time.sleep(1)
        