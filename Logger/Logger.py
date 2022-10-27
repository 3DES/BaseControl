import time
import inspect
import logging
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
        def __lt__(self, other):
            if self.__class__ is other.__class__:
                result = self.value < other.value
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " < " + str(other.__class__))
        def __le__(self, other):
            if self.__class__ is other.__class__:
                result = self.value <= other.value
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " <= " + str(other.__class__))
        def __gt__(self, other):
            if self.__class__ is other.__class__:
                result = self.value > other.value
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " > " + str(other.__class__))
        def __ge__(self, other):
            if self.__class__ is other.__class__:
                result = self.value >= other.value
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " >= " + str(other.__class__))
        def __eq__(self, other):
            if self.__class__ is other.__class__:
                result = self.value == other.value
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " == " + str(other.__class__))
        def __ne__(self, other):
            if self.__class__ is other.__class__:
                result = not(self.value == other.value)
                return result
            self.raiseException("cannot compare " + str(self.__class__) + " != " + str(other.__class__))


    logQueue = None     # this alowes us to be a "singleton"
    #logLevel = LOG_LEVEL.DEBUG
    logLevel = LOG_LEVEL.TRACE


    def __init__(self, threadName : str, configuration : dict, logger = None):
        if self.setLogQueue():
            # are whe the Logger or was our __init__ just called by a sub class?
            super().__init__(threadName, configuration, self if logger is None else logger)

            self.logger.info(self, "init (Logger)")
        else:
            self.raiseException("Logger already instantiated, no further instances allowed")


    @classmethod
    def setLogQueue(cls):
        '''
        Setter for cls.logQueue
        '''
        setupResult = False
        with cls.threadLock:
            if cls.logQueue is None:
                cls.logQueue = Queue()               # create logger queue
                setupResult = True
        return setupResult


    @classmethod
    def writeLogQueue(cls):
        '''
        Some kind of setter for cls.logQueue
        '''
        # @todo noch ausprogrammieren!!!
        cls.logQueue.put()


    def threadMethod(self):
        self.logger.trace(self, "I am the Logger thread")
        time.sleep(0.3)


    @classmethod
    def setLogLevel(cls, newLogLevel : LOG_LEVEL):
        with cls.threadLock:
            if newLogLevel > Logger.LOG_LEVEL.DEBUG.value:
                newLogLevel = Logger.LOG_LEVEL.DEBUG
            cls.logLevel = Logger.LOG_LEVEL(newLogLevel)


    @classmethod
    def getSenderName(cls, sender):
        senderName = ""
        if hasattr(sender, "name"):
            senderName = "THREAD " + sender.name
        elif isinstance(sender, str):
            senderName = "STRING " + sender
        elif hasattr(sender, "__class__"):
            senderType = "CLASS  "
            if (sender.__module__ == 'builtins'):
                senderName = senderType + sender.__qualname__
            else:
                senderName = senderType + sender.__module__ + "." + sender.__name__
        #elif hasattr(sender, "__name__"):
        #    return sender.__name__
        else:
            self.raiseException("unknown caller: " + str(sender))

        return senderName


    @classmethod
    def debug(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.DEBUG, sender, data)


    @classmethod
    def trace(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.TRACE, sender, data)


    @classmethod
    def warning(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.WARN, sender, data)


    @classmethod
    def info(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.INFO, sender, data)


    @classmethod
    def error(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.ERROR, sender, data)


    @classmethod
    def fatal(cls, sender, data : str):
        cls.message(Logger.LOG_LEVEL.FATAL, sender, data)


    @classmethod
    def message(cls, level : int, sender, data : str):
        senderName = cls.getSenderName(sender)
        if level <= cls.logLevel:
            message = "Logger : " + senderName + " [" + str(level) + "] " + data
            print(message)
        if level == cls.LOG_LEVEL.ERROR:
            #logging.error()
            pass
        elif level == cls.LOG_LEVEL.FATAL:
            #logging.critical()
            pass
        # @todo add timestamp xxxxxxxxxxxxxxxxxxx
        # @todo write to queue


    @classmethod
    def getLogQueue(cls):
        if cls.logQueue is None:
            self.raiseException("logger queue not yet set up")

        return cls.logQueue

