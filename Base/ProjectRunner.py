'''
'''


import traceback
import time
import logging
from signal import signal
from signal import SIGINT
import json
import sys

import Worker.Worker
import Logger.Logger
import MqttBridge.MqttBridge
import WatchDog.WatchDog
import Base.Base
import Base.ThreadBase
from Base.Supporter import Supporter
from Base.ExtendedJsonParser import ExtendedJsonParser
from Base.Debugger import Debugger
import Logger
import os
import colorama


# install signal handler
signalReceived = False
 
# handle sigint
def custom_handler(signum, frame):
    additionalText = ""
    if signum == 2:
        additionalText = " (=Ctrl+C)"
    Logger.Logger.Logger.fatal(custom_handler, f"Signal {signum}{additionalText} received, will stop working as soon as possible")
    global signalReceived
    signalReceived = True

# register the signal handler for control-c
signal(SIGINT, custom_handler)


class ProjectRunner(object):
    '''
    classdocs
    '''


    executed = False                # set to True after first execution
    projectLogger  = None
    projecDebugger = None
    projectMqttBridge = None
    threadStartOrder = []
    threadDictionary = None


    def __init__(self):
        '''
        Constructor not needed and, therefore, not allowed to be called

        :raises Exception: if it is called even it shouldn't
        '''
        raise Exception("object " + self.name + " has already registered to an MqttBridge")("ProjectRunner __init__() should never be called")


    @classmethod
    def setupThreads(cls, threadDictionary : dict, startupPriorities : dict, loggerName : str, mqttBridgeName : str, debuggerName : str):
        '''
        Sets up all threads in defined order, order has to be defined via init.json file, usually the following order is recommended:
            1. Logger
            2. MqttBridge
            3. Debugger
            4. WatchDog
            5. all not prioritized tasks
            6. Worker
        '''
        cls.threadDictionary = threadDictionary
        for priority in sorted(startupPriorities.keys()):
            for threadName in sorted(startupPriorities[priority]):
                # create thread
                thread = threadDictionary[threadName]["class"](
                    threadName,
                    threadDictionary[threadName]["configuration"])
                threadDictionary[threadName]["thread"] = thread

                # remember important threads
                if threadName == loggerName:
                    cls.projectLogger = thread
                elif threadName == mqttBridgeName:
                    cls.projectMqttBridge = thread
                elif (debuggerName is not None) and (threadName == debuggerName):
                    cls.projecDebugger = thread

                # finally start thread
                cls.threadStartOrder.append(threadName)
                thread.start()

                if "startPollingTime" in threadDictionary[threadName]["configuration"]:
                    if (threadDictionary[threadName]["configuration"]["startPollingTime"] == "infinite") or (type(threadDictionary[threadName]["configuration"]["startPollingTime"]) == int):
                        # "infinite" is supported here but can cause other errors, e.g. timeout in watchdog!
                        POLLING_TIME = threadDictionary[threadName]["configuration"]["startPollingTime"]
                    else:
                        raise Exception(f"startPollingTime {threadDictionary[threadName]['configuration']['startPollingTime']} given for object {threadName} is not supported!")
                else:
                    POLLING_TIME = 20     # 20 seconds should be enough

                # wait until thread has been finished initialization
                POLLING_SLEEP_TIME = .1     # sleep of .1 seconds per poll
                while not thread.threadInitializationFinished() and POLLING_TIME and not cls.checkThreadsException():
                    time.sleep(.1)
                    if type(POLLING_TIME) == int:
                        POLLING_TIME -= POLLING_SLEEP_TIME
                        if POLLING_SLEEP_TIME < 0:
                            # just to be sure while comes to an end, because e.g. "1 - n * 0.3" will never become 0
                            POLLING_SLEEP_TIME = 0
                if cls.checkThreadsException():
                    raise Exception(f"got exception while starting thread {threadName}: {Base.ThreadBase.ThreadBase.get_exception()}")
                if not thread.threadInitializationFinished():
                    raise Exception(f"starting up thread {threadName} took longer than {POLLING_TIME} seconds, please fix this!")

        cls.projectLogger.info(cls, f"all threads up and running, started in following order: {cls.threadStartOrder}")
        Supporter.debugPrint(f"all threads up and running, started in following order: {cls.threadStartOrder}", color = "LIGHTGREEN")

        # if a debugger has been defined set thread dictionary for watching thread variables
        if cls.projecDebugger is not None:
            cls.projecDebugger.setThreadDictionary(cls.threadDictionary)


    @classmethod
    def checkThreadsException(cls):
        return (Base.ThreadBase.ThreadBase.get_exception() is not None)


    @classmethod
    def monitorThreads(cls, stopAfterSeconds : int):
        # used to stop the monitoring loop if a maximum running time has been given
        startTime = Supporter.getTimeStamp()
        running = True

        # loop until any thread throws an exception (and for debugging after 5 seconds)
        while (not cls.checkThreadsException()) and running and not signalReceived:
            time.sleep(1)     # that's fast enough!

            cls.projectLogger.trace(cls, "alive")
            if stopAfterSeconds:
                if Supporter.getSecondsSince(startTime) > stopAfterSeconds:
                    cls.projectLogger.info(cls, "overall stop since given running time is over")
                    Supporter.debugPrint(f"overall stop since given running time is over", color = "LIGHTRED")
                    running = False

        if cls.checkThreadsException():
            return "oh noooo, we got an exception"
        elif not running:
            return "running time is over"
        elif signalReceived:
            return "stopped via signal"


    @classmethod
    def createThreadDictionary(cls, configuration : dict):
        '''
        Search the two threads that have to be started up first
            #1 Logger
            #2 MqttBridge
        all others are started in the order they have been defined

        The worker thread is only searched to ensure it exists and there is only one of them, but there is no further special handling done with it
        '''
        threadDictionary = {}
        DEFAULT_PRIORITY = 0
        startupPriority  = { DEFAULT_PRIORITY : [] }       # 0 is default startup priority, all tasks without a "startPriority" given will be put into this list
        loggerName     = None
        debuggerName   = None
        mqttBridgeName = None
        workerName     = None

        # search through all defined objects and find logger and mqtt bridge and ensure there is always only one of them
        for threadName in configuration:
            # definition contains "class" key?
            if "class" in configuration[threadName]:
                # sort all tasks after startup priority
                if "startPriority" in configuration[threadName]:
                    if configuration[threadName]["startPriority"] not in startupPriority:
                        startupPriority[configuration[threadName]["startPriority"]] = []    # add empty list to add tasks with this priority
                    startupPriority[configuration[threadName]["startPriority"]].append(threadName)
                else:
                    startupPriority[DEFAULT_PRIORITY].append(threadName)

                threadConfiguration = configuration[threadName]                             # take configuration from init file
                fullClassName = threadConfiguration["class"]                                # get class type

                loadableClass = Supporter.loadClassFromFile(fullClassName)

                # search special threads and ensure there are not more than one of them, furthermore ensure all threads are sub classes of ThreadBase
                if issubclass(loadableClass, Logger.Logger.Logger):
                    # only one system wide Logger is allowed
                    if loggerName is None:
                        loggerName = threadName
                    else:
                        raise Exception("init file contains more than one Logger, at least [" + loggerName + "] and [" + threadName + "]")
                elif issubclass(loadableClass, MqttBridge.MqttBridge.MqttBridge):
                    # only one system wide MqttBridge is allowed
                    if mqttBridgeName is None:
                        mqttBridgeName = threadName
                    else:
                        raise Exception("init file contains more than one MqttBridge, at least [" + mqttBridgeName + "] and [" + threadName + "]")
                elif issubclass(loadableClass, Worker.Worker.Worker):
                    # only one system wide Worker is allowed
                    if workerName is None:
                        workerName = threadName
                    else:
                        raise Exception("init file contains more than one Worker, at least [" + workerName + "] and [" + threadName + "]")
                elif issubclass(loadableClass, Base.Debugger.Debugger):
                    # only one system wide Worker is allowed
                    if debuggerName is None:
                        debuggerName = threadName
                    else:
                        raise Exception("init file contains more than one Debugger, at least [" + debuggerName + "] and [" + threadName + "]")
                elif not issubclass(loadableClass, Base.ThreadBase.ThreadBase):
                    # init file error found
                    raise Exception("init file contained class [" + threadName + "] is not a sub class of [Base.ThreadBase.ThreadBase]")

                # since a json object is a dict each thread name is unique (even if it isn't inside init file but duplicates will get lost!)
                threadDictionary[threadName] = { "class" : loadableClass, "configuration" : configuration[threadName] }
            else:
                raise Exception("definition " + threadName + " doesn't contain a \"class\" key")

        # ensure all necessary threads have been defined
        if loggerName is None:
            raise Exception("missing any Logger in init file")
        if debuggerName is None:
            pass    # debugger is optional, so no problem here if it hasn't been given
        if mqttBridgeName is None:
            raise Exception("missing any MqttBridge in init file")
        if workerName is None:
            raise Exception("missing any Worker in init file")

        return (threadDictionary, startupPriority, loggerName, mqttBridgeName, debuggerName)


    @classmethod
    def executeProject(cls, initFileName : str, logFileName : str, logLevel : int, printLogLevel : int, logFilter : str, stopAfterSeconds : int, writeLogToDiskWhenEnds : bool, missingImportMeansError : bool, jsonDump : bool, jsonDumpFilter : str = None, additionalLeadIn : str = "", simulationAllowed : bool = False):
        '''
        Analyzes given init file and starts threads in well defined order

        It ensures that only one Logger thread, one MqttBridge thread and one Worker thread (or a subclass) has been defined.
        Logger will be executed first since all other threads need it for logging
        MqttBridge will be the second one since all other threads need it for inter-thread communication
        '''
        # ensure this method is called only once!
        if cls.executed:
            raise Exception("don't call executeProject() more than once")
        else:
            cls.executed = True

        startTime = Supporter.getTimeStamp()

        # set some command line parameters to the referring threads
        Logger.Logger.Logger.set_logLevel(logLevel)
        Logger.Logger.Logger.set_printLogLevel(printLogLevel)
        Logger.Logger.Logger.set_logFilter(logFilter)
        Base.Base.Base.setSimulationModeAllowed(simulationAllowed)

        configuration = Supporter.loadInitFile(initFileName, missingImportMeansError)
        readableJsonConfiguration = json.dumps(configuration, indent = 4)

        print(f"python version information: {sys.version}")     # prints python version and GCC version pyhton was built with

        extendedJsonParser = ExtendedJsonParser()
        readableJsonConfiguration = json.dumps(extendedJsonParser.parse(readableJsonConfiguration, protectRegex = jsonDumpFilter), indent = 4)
        if jsonDump:
            print(readableJsonConfiguration)

        stopReason = ""

        try:
            # validate init file content, load all classes and filter certain special classes (i.e. Logger, MqttBridge and Logger)
            (threadDictionary, startupPriorities, loggerName, mqttBridgeName, debuggerName) = cls.createThreadDictionary(configuration)

            # now threads will be instantiated and stared, if any exception happens now we have to tear them down again!
            try:
                # now really setup all the threads
                #print(threadDictionary)
                cls.setupThreads(threadDictionary, startupPriorities, loggerName, mqttBridgeName, debuggerName)
                stopReason = cls.monitorThreads(stopAfterSeconds)        # "endless" while loop
            except Exception as exception:
                Logger.Logger.Logger.error(cls, f"INSTANTIATE/RUNNING EXCEPTION {exception}" + traceback.format_exc())
                #logging.exception("INSTANTIATE EXCEPTION " + traceback.format_exc())

            Base.ThreadBase.ThreadBase.stopAllThreads()
        except Exception:
            Logger.Logger.Logger.error(cls, "SETUP EXCEPTION " + traceback.format_exc())
            #logging.exception("SETUP EXCEPTION " + traceback.format_exc())


        endTime = Supporter.getTimeStamp()

        # in error case try to write the log buffer content out to disk
        if cls.checkThreadsException() or writeLogToDiskWhenEnds or signalReceived:
            deltaTime = endTime - startTime
            uptimeMessage = f"{os.path.basename(__file__)}: overall uptime ... {Supporter.formattedTime(deltaTime, addCurrentTime = True)}"
            Supporter.debugPrint(uptimeMessage, color = f"{colorama.Fore.RED}")

            additionalLeadIn += f"\npython version information: {sys.version}"
            if jsonDump:
                additionalLeadIn += "\n" + readableJsonConfiguration

            cls.projectLogger.writeLogBufferToDisk(logFileName = logFileName, leadIn = additionalLeadIn, leadOut = uptimeMessage)
        return stopReason


