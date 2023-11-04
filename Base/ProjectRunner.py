'''
'''


import traceback
import time
import logging
from signal import signal
from signal import SIGINT
import json


import Worker.Worker
import Logger.Logger
import MqttBridge.MqttBridge
import WatchDog.WatchDog
import Base.ThreadBase
from Base.Supporter import Supporter
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
    projectLogger = None
    projectMqttBridge = None


    def __init__(self):
        '''
        Constructor not needed and, therefore, not allowed to be called

        :raises Exception: if it is called even it shouldn't
        '''
        raise Exception("object " + self.name + " has already registered to an MqttBridge")("ProjectRunner __init__() should never be called")


    @classmethod
    def setupThreads(cls, threadDictionary : dict, loggerName : str, mqttBridgeName : str):
        '''
        Setups up all threads in necessary order
          1) a Logger will be set up since all other threads need it
          2) a MqttBridge will be set up  since all other threads need it, since logger was already created it gets the MqttBridge set afterwards
          3) all other threads are setup and all except WatchDogs are started
          4) all watchdogs will get started with a list of all the threads setup up so far
        '''
        # setup logger thread first to enable logging as soon as possible
        cls.projectLogger     = threadDictionary[loggerName]["class"](
            loggerName,
            threadDictionary[loggerName]["configuration"])
        cls.projectLogger.start()
        threadDictionary.pop(loggerName)

        # setup mqtt bridge thread
        cls.projectMqttBridge = threadDictionary[mqttBridgeName]["class"](
            mqttBridgeName,
            threadDictionary[mqttBridgeName]["configuration"])
        cls.projectMqttBridge.start()
        threadDictionary.pop(mqttBridgeName)

        for threadName in threadDictionary:
            thread = threadDictionary[threadName]["class"](
                threadName,
                threadDictionary[threadName]["configuration"])
            thread.start()

        cls.projectLogger.info(cls, "all threads up and running")


    @classmethod
    def monitorThreads(cls, stopAfterSeconds : int):
        # used to stop the monitoring loop if a maximum running time has been given
        startTime = Supporter.getTimeStamp()
        running = True

        # loop until any thread throws an exception (and for debugging after 5 seconds)
        while (Base.ThreadBase.ThreadBase.get_exception() is None) and running and not signalReceived:
            time.sleep(1)     # that's fast enough!

            cls.projectLogger.trace(cls, "alive")
            if stopAfterSeconds:
                if Supporter.getSecondsSince(startTime) > stopAfterSeconds:
                    cls.projectLogger.info(cls, "overall stop since given running time is over")
                    running = False

        if Base.ThreadBase.ThreadBase.get_exception() is not None:
            return "oh noooo, we got an excepiton"
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
        loggerName = None
        mqttBridgeName = None
        workerName = None

        # search through all defined objects and find logger and mqtt bridge and ensure there is always only one of them
        for threadName in configuration:
            # definition contains "class" key?
            if "class" in configuration[threadName]:
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
        if mqttBridgeName is None:
            raise Exception("missing any MqttBridge in init file")
        if workerName is None:
            raise Exception("missing any Worker in init file")

        return (threadDictionary, loggerName, mqttBridgeName)


    @classmethod
    def executeProject(cls, initFileName : str, logLevel : int, printLogLevel : int, logFilter : str, stopAfterSeconds : int, writeLogToDiskWhenEnds : bool, missingImportMeansError : bool, jsonDump : bool, additionalLeadIn : str = ""):
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

        configuration = Supporter.loadInitFile(initFileName, missingImportMeansError)
        readableJsonConfiguration = json.dumps(configuration, indent = 4)
        if jsonDump:
            print(readableJsonConfiguration)

        stopReason = ""

        try:
            # validate init file content, load all classes and filter certain special classes (i.e. Logger, MqttBridge and Logger)
            (threadDictionary, loggerName, mqttBridgeName) = cls.createThreadDictionary(configuration)

            # now threads will be instantiated and stared, if any exception happens now we have to tear them down again!
            try:
                # now really setup all the threads
                #print(threadDictionary)
                cls.setupThreads(threadDictionary, loggerName, mqttBridgeName)
                stopReason = cls.monitorThreads(stopAfterSeconds)        # "endless" while loop
            except Exception:
                Logger.Logger.Logger.error(cls, "INSTANTIATE/RUNNING EXCEPTION " + traceback.format_exc())
                #logging.exception("INSTANTIATE EXCEPTION " + traceback.format_exc())

            Base.ThreadBase.ThreadBase.stopAllThreads()
        except Exception:
            Logger.Logger.Logger.error(cls, "SETUP EXCEPTION " + traceback.format_exc())
            #logging.exception("SETUP EXCEPTION " + traceback.format_exc())


        endTime = Supporter.getTimeStamp()

        # in error case try to write the log buffer content out to disk
        if Base.ThreadBase.ThreadBase.get_exception() is not None or writeLogToDiskWhenEnds or signalReceived:
            deltaTime = endTime - startTime
            uptimeMessage = f"{os.path.basename(__file__)}: overall uptime ... {Supporter.formattedTime(deltaTime, addCurrentTime = True)}"
            Supporter.debugPrint(uptimeMessage, color = f"{colorama.Fore.RED}")

            cls.projectLogger.writeLogBufferToDisk(leadIn = additionalLeadIn + (("\n" + readableJsonConfiguration) if jsonDump else ""), leadOut = uptimeMessage)
        return stopReason


