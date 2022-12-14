import time
import inspect
import logging
import collections
from enum import Enum
import queue
from queue import Queue
from datetime import datetime
import Base
import re
from Base.Supporter import Supporter


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
            raise Exception("cannot compare " + str(self.__class__) + " < " + str(other.__class__))
        def __le__(self, other):
            if self.__class__ is other.__class__:
                result = self.value <= other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " <= " + str(other.__class__))
        def __gt__(self, other):
            if self.__class__ is other.__class__:
                result = self.value > other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " > " + str(other.__class__))
        def __ge__(self, other):
            if self.__class__ is other.__class__:
                result = self.value >= other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " >= " + str(other.__class__))
        def __eq__(self, other):
            if self.__class__ is other.__class__:
                result = self.value == other.value
                return result
            raise Exception("cannot compare " + str(self.__class__) + " == " + str(other.__class__))
        def __ne__(self, other):
            if self.__class__ is other.__class__:
                result = not(self.value == other.value)
                return result
            raise Exception("cannot compare " + str(self.__class__) + " != " + str(other.__class__))


    __logQueue_always_use_getters_and_setters       = None                          # to be a "singleton"
    __logQueueLength_always_use_getters_and_setters = 100                           # can be overwritten via ini file entry
    __logLevel_always_use_getters_and_setters       = LOG_LEVEL.DEBUG               # will be overwritten in __init__
    __logBuffer_always_use_getters_and_setters      = collections.deque([], 500)    # length of 500 elements
    __printAlways_always_use_getters_and_setters    = False                         # print log messages always even if level is not LOG_LEVEL.DEBUG
    __preLogBuffer_always_use_getters_and_setters   = []                            # list to collect all log messages created before logger has been started up (they should be printed too for the case the logger will never come up!), if the logger comes up it will log all these messages first!
    __logFilter_always_use_getters_and_setters      = r""                           # filter regex

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
                raise Exception("Logger already instantiated, no further instances allowed")


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
    def set_logFilter(cls, newLogFilter : str):
        '''
        To change log filter, e.g. during development to show messages only from a certain thread
        '''
        with cls.get_threadLock():
            Logger._Logger__logFilter_always_use_getters_and_setters = newLogFilter


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
#            if (len(Logger._Logger__logBuffer_always_use_getters_and_setters) > 100):
#                raise Exception("test exception")
# eine Loesung waere vor dem Schreiben in die Queue zu pruefen ob eine Exception ansteht und dann nicht mehr schreiben, dann klappt zwar das runterfahren, man erhaelt aber trotzdem keine Messages mehr...
#         if not Base.ThreadBase.ThreadBase.get_exception():


    @classmethod
    def get_logBuffer(cls):
        '''
        To add a log message to log buffer
        '''
        return Logger._Logger__logBuffer_always_use_getters_and_setters


    @classmethod
    def add_preLogMessage(cls, logEntry : str):
        '''
        To add a log message before logger has been set up, logger should handle them first when it comes up
        '''
        print("(P) " + logEntry)        # (P) means pre-logged message printed to STDOUT
        with cls.get_threadLock():
            Logger._Logger__preLogBuffer_always_use_getters_and_setters.append(logEntry)


    @classmethod
    def get_preLogMessage(cls) -> str:
        '''
        To add a log message before logger has been set up, logger should handle them first when it comes up
        '''
        with cls.get_threadLock():
            if len(Logger._Logger__preLogBuffer_always_use_getters_and_setters):
                return Logger._Logger__preLogBuffer_always_use_getters_and_setters.pop(0)
            else:
                return None


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None, logger = None):
        '''
        Logger constructor
        
        the optional logger parameter is for the case that we have a sub class that inherited from us and is, therefore, the real logger!
        '''
        # check and prepare mandatory parameters
        self.tagsIncluded(["projectName"], configuration = configuration)
        self.set_projectName(configuration["projectName"])
        if self.tagsIncluded(["queueLength"], optional = True, configuration = configuration):
            self.set_logQueueLength(configuration["queueLength"])
        if not self.tagsIncluded(["homeAutomation"], optional = True, configuration = configuration):
            configuration["homeAutomation"] = "HomeAutomation.BaseHomeAutomation.BaseHomeAutomation"

        self.setup_logQueue()                                   # setup log queue
        self.logBuffer = collections.deque([], 500)             # buffer storing the last 500 elements (for emergency write)
        self.logCounter = 0                                     # counts all logged messages
        self.set_logger(self if logger is None else logger)     # set project wide logger (since this is the base class for all loggers its it's job to set the project logger)
        self.set_homeAutomation(Supporter.loadClassFromFile(configuration["homeAutomation"])())
        self.logQueueMaximumFilledLength = 0                    # to monitor queue fill length (for system stability)

        # now call super().__init() since all necessary pre-steps have been done
        super().__init__(threadName, configuration, interfaceQueues)

        self.logger.info(self, "init (Logger)")


    def _handleMessage(self, newLogEntry : str):
        '''
        Handles the given log entry and returns True in case it has been logged or False in case it has been ignored because of log level
        '''
        self.logCounter += 1;

        self.add_logMessage(newLogEntry)
        
        if (self.get_logLevel() == Logger.LOG_LEVEL.DEBUG) or self.get_printAlways():
            if (not "messageFilter" in self.configuration) or re.search(self.configuration["messageFilter"], newLogEntry):
                print("#" + str(self.logCounter) + " " + newLogEntry)   # print is OK here!
                return True
        
        return False


    def threadInitMethod(self):
        while True:
            newLogEntry = self.get_preLogMessage()
            if newLogEntry is None:
                break
            self._handleMessage(newLogEntry)


    def threadMethod(self):
        # get queue length for monitoring
        queueLength = self.get_logQueue().qsize()

        printLine = False
        while not self.get_logQueue().empty():      # @todo ggf. sollten wir hier nur max. 100 Messages behandeln und danach die Loop verlassen, damit die threadLoop wieder dran kommt, andernfalls koennte diese komplett ausgehebelt werden
            newLogEntry = self.get_logQueue().get(block = False)
            printLine = self._handleMessage(newLogEntry)

        # after the queue handling loop has (hopefully) cleared the loop it's ok to send a warning message now
        if self.logQueueMaximumFilledLength < queueLength:
            self.logQueueMaximumFilledLength = queueLength
            if self.logQueueMaximumFilledLength > .8 * self.get_logQueueLength():
                self.logger.warning(self, "logger queue fill level is very high: " + str(queueLength) + " of " + str(self.get_logQueueLength())) 

        if printLine:
            print("--------------")     # print is OK here


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
            raise Exception("unknown caller: " + str(sender))

        return senderName


    @classmethod
    def debug(cls, sender, message):
        '''
        To log a debug message
        '''
        cls.message(Logger.LOG_LEVEL.DEBUG, sender, message)


    @classmethod
    def trace(cls, sender, message):
        '''
        To log a trace message, usually to be used to see the steps through setup and tear down process as well as to see the threads working
        '''
        cls.message(Logger.LOG_LEVEL.TRACE, sender, message)


    @classmethod
    def info(cls, sender, message):
        '''
        To log any information that could be from interest
        '''
        cls.message(Logger.LOG_LEVEL.INFO, sender, message)


    @classmethod
    def warning(cls, sender, message):
        '''
        To log any warnings
        '''
        cls.message(Logger.LOG_LEVEL.WARN, sender, message)


    @classmethod
    def error(cls, sender, message):
        '''
        To log an error, usually in case of exceptions, that's usually the highest error level for any problems in the script
        '''
        cls.message(Logger.LOG_LEVEL.ERROR, sender, message)


    @classmethod
    def fatal(cls, sender, message):
        '''
        To log an fatal errors, usually by detecting real critical hardware problems
        '''
        cls.message(Logger.LOG_LEVEL.FATAL, sender, message)


    @classmethod
    def get_filter(cls):
        return Logger._Logger__logFilter_always_use_getters_and_setters
        
    @classmethod
    def filter(cls, sender):
        filterPattern = cls.get_filter()
        length = (len(filterPattern) == 0)
        matched = (re.search(filterPattern, sender) is not None)
        return (len(filterPattern) == 0) or (re.search(filterPattern, sender) is not None)


    @classmethod
    def message(cls, level : LOG_LEVEL, sender, message):
        '''
        Overall log method, all log methods have to end up here
        '''
        if level <= cls.get_logLevel():
            if isinstance(sender, str):
                senderName = sender
            else:
                senderName = cls.getSenderName(sender)
            timeStamp = datetime.now()
            levelText = "{:<18}".format("[" + str(level) + "]")

            if not isinstance(message, str):
                message = str(message)

            logMessage = str(timeStamp) + "  " + levelText + " \"" + senderName + "\" : " + message

            preLogged = False       # in case logger is not running the given message is pre-logged and in case of error or fatal it is additionally printed to STDOUT!

            if cls.filter(senderName) or (level <= cls.LOG_LEVEL.ERROR):
                if cls.get_logQueue() is not None:
                    # send message to log
                    cls.get_logQueue().put(logMessage, block = False)
                else:
                    # Queue is not yet available so log message into pre-log buffer instead
                    cls.add_preLogMessage(logMessage)
                    preLogged = True

            if level == cls.LOG_LEVEL.ERROR:
                logging.error(logMessage)
                if not preLogged:     # only print if not pre-logged to suppress double printing
                    print("(E) " + logMessage)      # (E) means error printed to STDOUT
            elif level == cls.LOG_LEVEL.FATAL:
                logging.critical(logMessage)
                if not preLogged:     # only print if not pre-logged to suppress double printing
                    print("(F) " + logMessage)      # (W) means fatal error printed to STDOUT


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
