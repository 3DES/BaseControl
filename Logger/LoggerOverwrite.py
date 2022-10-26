import time
from Logger.Logger import Logger


class LoggerOverwrite(Logger):
    def __init__(self, threadName : str, configuration : dict, logger = None):
        super().__init__(threadName, configuration, self if logger is None else logger)
        self.x(self.LOG_LEVEL.TRACE, self.name, "LoggerOverwrite init")


    def threadMethod(self):
        self.x(self.logger.LOG_LEVEL.TRACE, self.name, "I am LoggerOverwrite thread")
        time.sleep(0.3)


    @classmethod
    def x(cls, level : int, sender : str, data : str):
        print("LoggerOverwrite.x() : " + sender + " [" + str(level) + "] " + data)
        # @todo write to queue

