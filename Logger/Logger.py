import time
import inspect
import os
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
        NONE  = -1
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


    __logQueue_always_use_getters_and_setters       = None                          # ensures Logger is a "singleton"
    __logLevel_always_use_getters_and_setters       = LOG_LEVEL.DEBUG               # default is log everything
    __printLogLevel_always_use_getters_and_setters  = LOG_LEVEL.NONE                # default is print nothing
    __logBuffer_always_use_getters_and_setters      = collections.deque([], 10000)  # length of 10000 elements
    __preLogBuffer_always_use_getters_and_setters   = []                            # list to collect all log messages created before logger has been started up (they should be printed too for the case the logger will never come up!), if the logger comes up it will log all these messages first!
    __logFilter_always_use_getters_and_setters      = r""                           # filter regex for what logs will be logged
    __printLogFilter_always_use_getters_and_setters = r""                           # filter regex for what logs will be printed (what is not logged cannnot be printed, so log filter go first!)


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
                Logger._Logger__logQueue_always_use_getters_and_setters = Queue(Base.Base.Base.QUEUE_SIZE + Base.Base.Base.QUEUE_SIZE_EXTRA)          # create logger queue
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
            elif newLogLevel < Logger.LOG_LEVEL.NONE.value:
                newLogLevel = Logger.LOG_LEVEL.NONE.value
            Logger._Logger__logLevel_always_use_getters_and_setters = Logger.LOG_LEVEL(newLogLevel)


    @classmethod
    def get_printLogLevel(cls):
        '''
        Getter for __logLevel variable
        '''
        return Logger._Logger__printLogLevel_always_use_getters_and_setters


    @classmethod
    def set_printLogLevel(cls, newPrintLogLevel : int):
        '''
        To change log level, e.g. during development to show debug information or in productive state to hide too many log information nobody needs
        '''
        with cls.get_threadLock():
            if newPrintLogLevel > Logger.LOG_LEVEL.DEBUG.value:
                newPrintLogLevel = Logger.LOG_LEVEL.DEBUG.value
            elif newPrintLogLevel < Logger.LOG_LEVEL.NONE.value:
                newPrintLogLevel = Logger.LOG_LEVEL.NONE.value
            Logger._Logger__printLogLevel_always_use_getters_and_setters = Logger.LOG_LEVEL(newPrintLogLevel)


    @classmethod
    def set_printLogFilter(cls, newPrintLogFilter : str):
        '''
        To change print log filter, e.g. during development to show messages only from a certain thread
        '''
        with cls.get_threadLock():
            Logger._Logger__printLogFilter_always_use_getters_and_setters = newPrintLogFilter


    @classmethod
    def set_logFilter(cls, newLogFilter : str):
        '''
        To change log filter, e.g. during development to show messages only from a certain thread
        '''
        with cls.get_threadLock():
            Logger._Logger__logFilter_always_use_getters_and_setters = newLogFilter


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
    def add_preLogMessage(cls, logEntry : dict):
        '''
        To add a log message before logger has been set up, logger should handle them first when it comes up
        '''
        print("(P) " + logEntry["message"])        # (P) means pre-logged message printed to STDOUT
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
        self.tagsIncluded(["homeAutomation"], optional = True, configuration = configuration, default = "HomeAutomation.BaseHomeAutomation.BaseHomeAutomation")
        self.tagsIncluded(["homeAutomationPrefix"], optional = True, configuration = configuration, default = "")
        self.set_homeAutomation(Supporter.loadClassFromFile(configuration["homeAutomation"])(configuration["homeAutomationPrefix"]))

        self.setup_logQueue()                                   # setup log queue
        self.logCounter = 0                                     # counts all logged messages
        self.set_logger(self if logger is None else logger)     # set project wide logger (since this is the base class for all loggers its it's job to set the project logger)

        # now call super().__init() since all necessary pre-steps have been done
        super().__init__(threadName, configuration, interfaceQueues)

        self.removeMqttRxQueue()        # mqttRxQueue not needed so remove it

        self.logger.info(self, "init (Logger)")


#        print(f"timer: {self.timer('abc', timeout = 3)}")
#        time.sleep(1)
#        print(f"timer: {self.timer('abc')}")
#        time.sleep(1)
#        print(f"timer: {self.timer('abc')}")
#        time.sleep(1)
#        print(f"timer: {self.timer('abc')}")
#        time.sleep(1)

#        print(f"counter: {self.counter('foobar', value = 5)}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar')}")
#        print(f"counter: {self.counter('foobar', value = 5)}")
#        print(f"counter: {self.counter('foobar', value = 5)}")
#        print(f"counter: {self.counter('foobar', value = 5)}")
#        print(f"counter: {self.counter('foobar', value = 5)}")

#        print(f"accumulator: {self.accumulator('foobar', power = 21, useCounter = False, timeout = 5, synchronized = False, absolute = True, autoReset = True, minMaxAverage = True)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 23)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 25)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 27)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 29)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 31)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 27)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#        print(f"accumulator: {self.accumulator('foobar', power = 28)}")
#        time.sleep(1)
#
#        import sys
#        sys.exit()


    def _handleMessage(self, newLogEntry : dict):
        '''
        Handles the given log entry and returns True in case it has been logged or False in case it has been ignored because of log level
        '''
        self.logCounter += 1;

        message = newLogEntry["message"]
        level = newLogEntry["level"]
        senderName = newLogEntry["sender"]

        # add message number to new message
        message = "#" + str(self.logCounter) + " " + message

        # store message in log buffer
        self.add_logMessage(message)

        if self.filter(senderName, forPrinting = True) and (Logger.get_printLogLevel() >= level):
            if (not "messageFilter" in self.configuration) or re.search(self.configuration["messageFilter"], message):
                print(message)   # print is OK here!
                return True

        return False


    def threadInitMethod(self):
        while True:
            newLogEntry = self.get_preLogMessage()
            if newLogEntry is None:
                break
            self._handleMessage(newLogEntry)


    def threadMethod(self):
        printLine = False
        while not self.get_logQueue().empty():      # @todo ggf. sollten wir hier nur max. 100 Messages behandeln und danach die Loop verlassen, damit die threadLoop wieder dran kommt, andernfalls koennte diese komplett ausgehebelt werden
            newLogEntry = self.get_logQueue().get(block = False)
            printLine = self._handleMessage(newLogEntry)

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
            senderName = f"THREAD {sender.name}"
            className = ""
            if hasattr(sender, "__class__"):
                senderType = "CLASS  "
                if (sender.__module__ == 'builtins'):
                    className = sender.__qualname__
                else:
                    className = sender.__module__
                senderName += f" [{className}]"
        elif isinstance(sender, str):
            senderName = "STRING " + sender
        elif hasattr(sender, "__class__"):
            senderType = "CLASS  "
            if (sender.__module__ == 'builtins'):
                senderName = senderType + sender.__qualname__
            else:
                senderName = senderType + sender.__module__

                # add __name__ if available
                if hasattr(sender, "__name__"):
                    senderName += "." + sender.__name__
        #elif hasattr(sender, "__name__"):
        #    return sender.__name__
        else:
            raise Exception("unknown caller: " + str(sender))

        return senderName


    @classmethod
    def _caller(cls, skipExtra : int = 0):
        #return f" ({os.path.basename(inspect.stack()[2].filename)}:{inspect.stack()[2].lineno})"
        return f" ({Supporter.getCallerPosition(skip = 3 + skipExtra)})"    # skip some more levels to get real caller


    @classmethod
    def debug(cls, sender, message, skip : int = 0):
        '''
        To log a debug message
        '''
        cls._logMessage(Logger.LOG_LEVEL.DEBUG, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def trace(cls, sender, message, skip : int = 0):
        '''
        To log a trace message, usually to be used to see the steps through setup and tear down process as well as to see the threads working
        '''
        cls._logMessage(Logger.LOG_LEVEL.TRACE, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def info(cls, sender, message, skip : int = 0):
        '''
        To log any information that could be from interest
        '''
        cls._logMessage(Logger.LOG_LEVEL.INFO, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def warning(cls, sender, message, skip : int = 0):
        '''
        To log any warnings
        '''
        cls._logMessage(Logger.LOG_LEVEL.WARN, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def error(cls, sender, message, skip : int = 0):
        '''
        To log an error, usually in case of exceptions, that's usually the highest error level for any problems in the script
        '''
        #cls.message(Logger.LOG_LEVEL.ERROR, sender, message + cls._caller() + "\n" + Supporter.getCallStack())
        cls._logMessage(Logger.LOG_LEVEL.ERROR, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def fatal(cls, sender, message, skip : int = 0):
        '''
        To log an fatal errors, usually by detecting real critical hardware problems
        '''
        #cls.message(Logger.LOG_LEVEL.FATAL, sender, message + cls._caller() + "\n" + Supporter.getCallStack())
        cls._logMessage(Logger.LOG_LEVEL.FATAL, sender, message + cls._caller(skipExtra = skip))


    @classmethod
    def message(cls, method, sender, message):
        '''
        Call log method by name or by log level
        
        @param method    method name of the method or log level that should be handled
        '''
        LOG_METHODS = {
            "debug"   : cls.debug,
            "trace"   : cls.trace,
            "info"    : cls.info,
            "warning" : cls.warning,
            "error"   : cls.error,
            "fatal"   : cls.fatal
        }

        LOG_LEVELS = {
            Logger.LOG_LEVEL.DEBUG.value : cls.debug,  
            Logger.LOG_LEVEL.TRACE.value : cls.trace,  
            Logger.LOG_LEVEL.INFO.value  : cls.info,   
            Logger.LOG_LEVEL.WARN.value  : cls.warning,
            Logger.LOG_LEVEL.ERROR.value : cls.error,  
            Logger.LOG_LEVEL.FATAL.value : cls.fatal   
        }

        if type(method) == type(cls.LOG_LEVEL.DEBUG) and (method.value in LOG_LEVELS):
            #Supporter.debugPrint(f"redirect to {LOG_LEVELS[method.value]}")
            LOG_LEVELS[method.value].__get__(cls, cls)(sender, message, skip = 1)
        elif type(method) == str and (method in LOG_METHODS):
            #Supporter.debugPrint(f"redirect to {LOG_METHODS[method]}")
            LOG_METHODS[method].__get__(cls, cls)(sender, message, skip = 1)
        else:
            raise Exception(f"given log level or method name is unknown {method}")


    @classmethod
    def get_printLogFilter(cls):
        return Logger._Logger__printLogFilter_always_use_getters_and_setters


    @classmethod
    def get_logFilter(cls):
        return Logger._Logger__logFilter_always_use_getters_and_setters


    @classmethod
    def filter(cls, sender, forPrinting : bool = False):
        if not forPrinting:
            filterPattern = cls.get_logFilter()
        else:
            filterPattern = cls.get_printLogFilter()
        return (len(filterPattern) == 0) or (re.search(filterPattern, sender) is not None)


    @classmethod
    def _logMessage(cls, level : LOG_LEVEL, sender, message):
        '''
        Overall log method, all log methods have to end up here
        '''
        if level <= cls.get_logLevel():
            timeStamp = datetime.now()
            if isinstance(sender, str):
                senderName = sender
            else:
                senderName = cls.getSenderName(sender)
            levelText = "{:<18}".format("[" + str(level) + "]")

            if not isinstance(message, str):
                message = str(message)

            logMessage = {
                "message" : str(timeStamp) + "  " + levelText + " \"" + senderName + "\" : " + message,
                "level"   : level,
                "sender"  : senderName
            }

            preLogged = False       # in case logger is not running the given message is pre-logged and in case of error or fatal it is additionally printed to STDOUT!
            if cls.filter(senderName) or (level <= cls.LOG_LEVEL.ERROR):
                if cls.get_logQueue() is not None:
                    # ensure Logger gets enough time to handle its queue!
                    while (cls.get_logQueue().qsize() > Base.Base.Base.QUEUE_SIZE):
                        time.sleep(0)
                    # send message to log
                    cls.get_logQueue().put(logMessage, block = False)
                else:
                    # Queue is not yet available so log message into pre-log buffer instead
                    cls.add_preLogMessage(logMessage)
                    preLogged = True

            if level == cls.LOG_LEVEL.ERROR:
                logging.error(logMessage)
                if not preLogged:     # only print if not pre-logged to suppress double printing
                    print("(E) " + logMessage["message"])      # (E) means error printed to STDOUT
            elif level == cls.LOG_LEVEL.FATAL:
                logging.critical(logMessage)
                if not preLogged:     # only print if not pre-logged to suppress double printing
                    print("(F) " + logMessage["message"])      # (W) means fatal error printed to STDOUT


    @classmethod
    def writeLogBufferToDisk(cls, logFileName : str, leadIn : str = "", leadOut : str = ""):
        '''
        Without regard to losses the current buffer content is written to disk
        
        @param logFileName     logfile name to be used
        @param leadIn          string that will be inserted at the beginning of the logfile because, at times when this method is called, the logger queue usually doesn't work anymore
        @param leadOut         string that will be inserted at the end       of the logfile because, at times when this method is called, the logger queue usually doesn't work anymore
        '''
        def insertFramedText(text : str):
            data = []
            data.append("#" * 100) 
            data.append(text) 
            data.append("#" * 100) 
            return data


        bufferCopy = []

        # insert lead in
        if len(leadIn):
            bufferCopy += insertFramedText(leadIn)

        # take all collected messages from log buffer
        bufferCopy += cls.get_logBuffer().copy()

        # insert lead out
        if len(leadOut):
            bufferCopy += insertFramedText(leadOut)

        # finally write log file
        with open(logFileName, 'w') as logFile:
            for message in bufferCopy:
                logFile.write(message + "\n")

            logFile.close()
