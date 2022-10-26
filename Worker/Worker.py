import time
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class Worker(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "Worker init")


    def threadMethod(self):
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "I am Worker thread")
        time.sleep(1)
        