import time
import inspect
import logging
import collections
from enum import Enum
import queue
from queue import Queue
from datetime import datetime


from Base.ThreadBase import ThreadBase


class Logger(ThreadBase):
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
            raise Exception("cannot compare " + str(self.__class__) + " < " + str(other.__class__))    # xxx.raiseException
        def __le__(self, other):
            if self.__class__ is other.__class__:
                result = self.value <= other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " <= " + str(other.__class__))    # xxx.raiseException
        def __gt__(self, other):
            if self.__class__ is other.__class__:
                result = self.value > other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " > " + str(other.__class__))    # xxx.raiseException
        def __ge__(self, other):
            if self.__class__ is other.__class__:
                result = self.value >= other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " >= " + str(other.__class__))    # xxx.raiseException
        def __eq__(self, other):
            if self.__class__ is other.__class__:
                result = self.value == other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " == " + str(other.__class__))    # xxx.raiseException
        def __ne__(self, other):
            if self.__class__ is other.__class__:
                result = not(self.value == other.value)
                return result
            raise Exception("cannot compare " + str(self.__class__) + " != " + str(other.__class__))    # xxx.raiseException


    __logQueue_always_use_getters_and_setters       = None                           # to be a "singleton"
    __logQueueLength_always_use_getters_and_setters = 100                            # can be overwritten via ini file entry
    __logLevel_always_use_getters_and_setters       = LOG_LEVEL.DEBUG                # will be overwritten in __init__
    __logBuffer_always_use_getters_and_setters      = collections.deque([], 500)     # length of 500 elements
    __printAlways_always_use_getters_and_setters    = False                          # print log messages always even if level is not LOG_LEVEL.DEBUG


    @classmethod
    def get_logQueueLength(cls):
        '''
        Getter for __logQueueLength variable
        '''
        return Logger._Logger__logQueueLength_always_use_getters_and_setters


    @classmethod
    def set_logQueueLength(cls, length : int):
        '''
        Setter for __logQueueLength variable
        '''
        Logger._Logger__logQueueLength_always_use_getters_and_setters = length


    @classmethod
    def get_logQueue(cls):
        '''
        Getter for __logQueue variable
        '''
        return Logger._Logger__logQueue_always_use_getters_and_setters


    @classmethod
    def setup_logQueue(cls):
        '''
        Prepares __logQueue variable
        '''
        with cls.get_threadLock():
            if Logger._Logger__logQueue_always_use_getters_and_setters is None:
                Logger._Logger__logQueue_always_use_getters_and_setters = Queue(cls.get_logQueueLength())          # create logger queue
            else:
                raise Exception("Logger already instantiated, no further instances allowed")    # self.raiseException


    @classmethod
    def get_logLevel(cls):
        '''
        Getter for __logLevel variable
        '''
        return Logger._Logger__logLevel_always_use_getters_and_setters


    @classmethod
    def set_logLevel(cls, newLogLevel : int):
        '''
        To change log level, e.g. during development to show debug information or in productive state to hide too many log information nobody needs
        '''
        with cls.get_threadLock():
            if newLogLevel > Logger.LOG_LEVEL.DEBUG.value:
                newLogLevel = Logger.LOG_LEVEL.DEBUG.value
            elif newLogLevel < Logger.LOG_LEVEL.ERROR.value:
                newLogLevel = Logger.LOG_LEVEL.DEBUG.value
            Logger._Logger__logLevel_always_use_getters_and_setters = Logger.LOG_LEVEL(newLogLevel)


    @classmethod
    def get_printAlways(cls):
        '''
        Getter for __logLevel variable
        '''
        return Logger.__printAlways_always_use_getters_and_setters


    @classmethod
    def set_printAlways(cls, printAlways : bool):
        '''
        To change log level, e.g. during development to show debug information or in productive state to hide too many log information nobody needs
        '''
        with cls.get_threadLock():
            Logger.__printAlways_always_use_getters_and_setters = printAlways


    @classmethod
    def add_logMessage(cls, logEntry : str):
        '''
        To add a log message to log buffer
        '''
        with cls.get_threadLock():
            Logger._Logger__logBuffer_always_use_getters_and_setters.append(logEntry)
# @todo diese Exception laesst sich nicht fangen!?!?
#            if (len(Logger._Logger__logBuffer_always_use_getters_and_setters) > 20):
#                raise Exception("test exception")


    @classmethod
    def get_logBuffer(cls):
        '''
        To add a log message to log buffer
        '''
        return Logger._Logger__logBuffer_always_use_getters_and_setters


    def __init__(self, threadName : str, configuration : dict, logger = None):
        '''
        Logger constructor
        
        the optional logger parameter is for the case that we have a sub class that inherited from us and is, therefore, the real logger!
        '''
        # are we the Logger or was our __init__ just called by a sub class?
        # check and prepare mandatory parameters
        if "projectName" not in configuration:
            raise Exception("Logger needs a projectName value in init file")  # self.raiseException
        self.set_projectName(configuration["projectName"])

        # check and prepare mandatory parameters
        if "queueLength" in configuration:
            configuration["queueLength"] = int(configuration["queueLength"])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)
            self.set_logQueueLength(configuration["queueLength"])
        
        self.setup_logQueue()                                   # setup log queue
        self.logBuffer = collections.deque([], 500)             # buffer storing the last 500 elements (for emergency write)
        self.logCoutner = 0                                     # counts all logged messages
        self.set_logger(self if logger is None else logger)     # set project wide logger (since this is the base class for all loggers its it's job to set the project logger)
        self.logQueueMaximumFilledLength = 0                    # to monitor queue fill length (for system stability)

        # now call super().__init() since all necessary pre-steps have been done
        super().__init__(threadName, configuration)

        self.logger.info(self, "init (Logger)")


    def threadMethod(self):
        self.logger.trace(self, "I am the Logger thread = " + self.name)

        # get queue length for monitoring
        queueLength = self.get_logQueue().qsize()

        printLine = False
        while not self.get_logQueue().empty():      # @todo ggf. sollten wir hier nur max. 100 Messages behandeln und danach die Loop verlassen, damit die threadLoop wieder dran kommt, andernfalls koennte diese komplett ausgehebelt werden
            self.logCoutner += 1;
            newLogEntry = self.get_logQueue().get(block = False)

            self.add_logMessage(newLogEntry)
            
            if (self.get_logLevel() == Logger.LOG_LEVEL.DEBUG) or self.get_printAlways():
                print("#" + str(self.logCoutner) + " " + newLogEntry)
                printLine = True

        # after the queue handling loop has (hopefully) cleared the loop it's ok to send a warning message now
        if self.logQueueMaximumFilledLength < queueLength:
            self.logQueueMaximumFilledLength = queueLength
            if self.logQueueMaximumFilledLength > .8 * self.get_logQueueLength():
                self.logger.warning(self, "logger queue fill level is very high: " + str(queueLength) + " of " + str(self.get_logQueueLength())) 

        if printLine:
            print("--------------")


    def threadBreak(self):
        time.sleep(.2)


    @classmethod
    def getSenderName(cls, sender):
        '''
        Try to create proper sender name usually for log messages
        '''
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
            raise Exception("unknown caller: " + str(sender))    # cls.raiseException

        return senderName


    @classmethod
    def debug(cls, sender, message : str):
        '''
    ....To log a debug message
        '''
        cls.message(Logger.LOG_LEVEL.DEBUG, sender, message)


    @classmethod
    def trace(cls, sender, message : str):
        '''
    ....To log a trace message, usually to be used to see the steps through setup and tear down process as well as to see the threads working
        '''
        cls.message(Logger.LOG_LEVEL.TRACE, sender, message)


    @classmethod
    def info(cls, sender, message : str):
        '''
    ....To log any information that could be from interest
        '''
        cls.message(Logger.LOG_LEVEL.INFO, sender, message)


    @classmethod
    def warning(cls, sender, message : str):
        '''
    ....To log any warnings
        '''
        cls.message(Logger.LOG_LEVEL.WARN, sender, message)


    @classmethod
    def error(cls, sender, message : str):
        '''
    ....To log an error, usually in case of exceptions, that's usually the highest error level for any problems in the script
        '''
        cls.message(Logger.LOG_LEVEL.ERROR, sender, message)


    @classmethod
    def fatal(cls, sender, message : str):
        '''
    ....To log an fatal errors, usually by detecting real critical hardware problems
        '''
        cls.message(Logger.LOG_LEVEL.FATAL, sender, message)


    @classmethod
    def message(cls, level : LOG_LEVEL, sender, message : str):
        '''
        Overall log method, all log methods have to end up here
        '''
        if level <= cls.get_logLevel():
            senderName = cls.getSenderName(sender)
            timeStamp = datetime.now()
            levelText = "{:<18}".format("[" + str(level) + "]")
            logMessage = str(timeStamp) + "  " + levelText + " \"" + senderName + "\" : " + message

            if cls.get_logQueue() is not None:
                cls.get_logQueue().put(logMessage, block = False)
            else:
                print(logMessage)           # Logger not yet set up so print message to STDOUT meanwhile

            if level == cls.LOG_LEVEL.ERROR:
                logging.error(logMessage)
                pass
            elif level == cls.LOG_LEVEL.FATAL:
                logging.critical(logMessage)
                pass


    @classmethod
    def writeLogBufferToDisk(cls, logFileName = None):
        '''
        Without regard to losses the current buffer content is written to disk 
        '''
        if logFileName is None:
            logFileName = "logger.txt"
        
        bufferCopy = cls.get_logBuffer().copy()
        
        with open(logFileName, 'w') as logFile:
            for message in bufferCopy:
                logFile.write(message + "\n")
            
            logFile.close()
