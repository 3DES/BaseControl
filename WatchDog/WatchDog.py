import time
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class WatchDog(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "WatchDog init")

    def threadMethod(self):
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "I am WatchDog thread")
        time.sleep(0.5)



