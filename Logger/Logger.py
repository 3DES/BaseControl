import time
from enum import Enum
from queue import Queue


from Base.ThreadInterface import ThreadInterface


class Logger(ThreadInterface):
    '''
    classdocs
    '''


    class LOG_LEVEL(Enum):
        FATAL = 0
        ERROR = 1
        WARN  = 2
        INFO  = 3
        TRACE = 4
        DEBUG = 5


    logQueue = None     # this alowes us to be a "singleton"


    def __init__(self, threadName : str, configuration : dict, logger = None):
        if self.logQueue is None:
            Logger.logQueue = Queue()               # create logger queue
            self.configuration = configuration      # remember given configuration

            super().__init__(threadName, configuration, self if logger is None else logger)

            self.x(self.logger.LOG_LEVEL.TRACE, self.name, "Logger init")
        else:
            self.x(self.LOG_LEVEL.FATAL, threadName, "Logger already instantiated, no further instance allowed")
            raise Exception("Logger already instantiated, no further instance allowed")


    def threadMethod(self):
        self.x(self.logger.LOG_LEVEL.TRACE, self.name, "I am Logger thread")
        time.sleep(0.3)


    @classmethod
    def x(cls, level : int, sender : str, data : str):
        print("Logger.x() : " + sender + " [" + str(level) + "] " + data)
        # @todo write to queue


    @classmethod
    def getLogQueue(cls):
        if cls.logQueue is None:
            raise Exception("logger queue not yet set up")

        return cls.logQueue

