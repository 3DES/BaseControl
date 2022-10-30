'''
'''


import pydoc
import json
import re
import traceback
import time
import logging


import Worker.Worker
import Logger.Logger
import MqttBridge.MqttBridge
import WatchDog.WatchDog
import Base.ThreadBase
from Base.Supporter import Supporter


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
    def loadClassFromFile(cls, fullClassName : str):
        '''
        loads a class from a given file
        no object will be created only the class will be loaded and given back to caller

        :param fullClassName: name of the class including package and module to be loaded (e.g. Logger.Logger.Logger means Logger class contained in Logger.py contained in Logger folder)
        :return: loaded but not yet instantiated class
        :rtype: module
        :raises Exception: if given module doesn't exist
        '''
        className = fullClassName.rsplit('.')[-1]
        classType = ".".join(fullClassName.rsplit('.')[0:-1])
        loadableModule = pydoc.locate(classType)

        if loadableModule is None:
            raise Exception("there is no module \"" + classType + "\"")

        print("loading: module = " + str(loadableModule) + ", className = " + str(className) + ", classType = " + str(classType))
        loadableClass = getattr(loadableModule, className)
        return loadableClass


    @classmethod
    def loadInitFile(cls, initFileName : str):
        '''
        reads a json file and since json doesn't support any comments all detected comments will be removed, i.e.
            # comment line                     -->   ""
            "a" : "b",    # trailing comment   -->   "a" : "b",
        '''
        initFile = open(initFileName)                           # open init file
        fileContent = ""
        for line in initFile:                                   # read line by line and remove comments
            line = line.rstrip('\r\n')                          # remove trailing CRs and NLs
            line = re.sub(r'#[^"\']*$', r'', line)             # remove comments, comments havn't to contain any quotation marks or apostrophes 
            line = re.sub(r'^ *#.*$', r'', line)                # remove line comments
            fileContent += line + "\n"                          # add filtered (or even empty line because of json error messages with line numbers) to overall json content
        initFile.close()
        return json.loads(fileContent)                          # now handle read content and return it to caller


    @classmethod
    def setupThreads(cls, threadDictionary : dict, loggerName : str, mqttBridgeName : str):
        '''
        Setups up all threads in correct order

        First a Logger will be set up since all other threads need it
        Second a MqttBridge will be set up  since all other threads need it, since logger was already created it gets the MqttBridge set afterwards
        Third a Worker will be set up since it's the master thread (maybe the worker should be the last one that is started?!)
        Fourth all other threads are setup and all except WatchDogs are started
        Fifth all watchdogs will get started with a list of all the threads setup up so far
        '''
        # setup logger thread first to enable logging as soon as possible
        cls.projectLogger     = threadDictionary[loggerName]["class"](
            loggerName,
            threadDictionary[loggerName]["configuration"])
        threadDictionary.pop(loggerName)
        
        # setup mqtt bridge thread
        cls.projectMqttBridge = threadDictionary[mqttBridgeName]["class"](
            mqttBridgeName,
            threadDictionary[mqttBridgeName]["configuration"],
            cls.projectLogger)
        threadDictionary.pop(mqttBridgeName)

        for threadName in threadDictionary:
            thread = threadDictionary[threadName]["class"](
                threadName,
                threadDictionary[threadName]["configuration"],
                cls.projectLogger)

        cls.projectLogger.info(cls, "all threads up and running")


    @classmethod
    def monitorThreads(cls, stopAfterSeconds : int):
        # used to stop the monitoring loop if a maximum running time has been given
        startTime = Supporter.getTimeStamp()
        running = True

        # loop until any thread throws an exception (and for debugging after 5 seconds)
        while (Base.ThreadBase.ThreadBase.get_exception() is None) and running:
            time.sleep(1)
            cls.projectLogger.trace(cls, "alive")
            if stopAfterSeconds:
                if Supporter.getTimeStamp() - startTime > stopAfterSeconds:
                    cls.projectLogger.info(cls, "overall stop since given running time is over")
                    running = False


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

                loadableClass = cls.loadClassFromFile(fullClassName)

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
    def executeProject(cls, initFileName : str, logLevel : int, stopAfterSeconds : int, printAlways : bool, writeLogToDiskWhenEnds : bool):
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

        # set some command line parameters to the referring threads
        Logger.Logger.Logger.set_logLevel(logLevel)
        Logger.Logger.Logger.set_printAlways(printAlways)

        configuration = cls.loadInitFile(initFileName)

        try:
            # validate init file content, load all classes and filter certain special classes (i.e. Logger, MqttBridge and Logger)
            (threadDictionary, loggerName, mqttBridgeName) = cls.createThreadDictionary(configuration)

            # now threads will be instantiated and stared, if any exception happens now we have to tear them down again!
            try:
                # now really setup all the threads
                #print(threadDictionary)
                cls.setupThreads(threadDictionary, loggerName, mqttBridgeName)
                cls.monitorThreads(stopAfterSeconds)        # "endless" while loop
            except Exception:
                print("INSTANTIATE/RUNNING EXCEPTION " + traceback.format_exc())
                #logging.exception("INSTANTIATE EXCEPTION " + traceback.format_exc())

            Base.ThreadBase.ThreadBase.stopAllThreads()
        except Exception:
            print("SETUP EXCEPTION " + traceback.format_exc())
            #logging.exception("SETUP EXCEPTION " + traceback.format_exc())


        # in error case try to write the log buffer content out to disk
        if Base.ThreadBase.ThreadBase.get_exception() is not None or writeLogToDiskWhenEnds:
            cls.projectLogger.writeLogBufferToDisk()

