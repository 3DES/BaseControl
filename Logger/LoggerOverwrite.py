import time
from Logger.Logger import Logger


class LoggerOverwrite(Logger):
    def __init__(self, threadName : str, configuration : dict, logger = None):
        '''
        Logger constructor
        
        the optional logger parameter is for the case that we have a sub class that inherited from us and is, therefore, the real logger!
        '''
        super().__init__(threadName, configuration, self if logger is None else logger)
        self.logger.info(self, "init (LoggerOverwrite)")


    def threadMethod(self):
        self.logger.trace(self, "I am the LoggerOverwrite thread = " + self.name)

        
    def threadBreak(self):
        time.sleep(0.3)


    @classmethod
    def message(cls, level : Logger.LOG_LEVEL, sender, data : str):
        print("LoggerOverwrite : " + sender + " [" + str(level) + "] " + data)
        # @todo wenn super.message fertig ist, dann diese Methode entsprechend anpassen!!!

