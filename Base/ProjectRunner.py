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
import Base.ThreadInterface
from Base.Supporter import Supporter


class ProjectRunner(object):
    '''
    classdocs
    '''


    executed = False                # set to True after first execution
    projectLogger = None
    projectWorker = None
    projectMqttBridge = None
    projectThreads = None


    def __init__(self):
        '''
        Constructor not needed and, therefore, not allowed to be called

        :raises Exception: if it is called even it shouldn't
        '''
        self.raiseException("object " + self.name + " has already registered to an MqttBridge")("ProjectRunner __init__() should never be called")


    @classmethod
    def raiseException(cls, string : str):
        raise Exception(string)


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
            cls.raiseException("there is no module \"" + classType + "\"")

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
            line = re.sub(r'#[^"\',]*$', r'', line)             # remove comments
            fileContent += line + "\n"                          # add filtered (or even empty line because of json error messages with line numbers) to overall json content
        initFile.close()
        return json.loads(fileContent)                          # now handle read content and return it to caller


    @classmethod
    def setupThreads(cls, threadDictionary : dict, loggerName : str, mqttBridgeName : str, workerName : str):
        cls.projectLogger     = threadDictionary[loggerName]["class"](
            loggerName,
            threadDictionary[loggerName]["configuration"])
        threadDictionary.pop(loggerName)
        cls.projectLogger.startThread()

        cls.projectMqttBridge = threadDictionary[mqttBridgeName]["class"](
            mqttBridgeName,
            threadDictionary[mqttBridgeName]["configuration"],
            cls.projectLogger)
        threadDictionary.pop(mqttBridgeName)
        cls.projectMqttBridge.startThread()

        cls.projectLogger.registerMqttBridge(cls.projectMqttBridge)

        cls.projectWorker     = threadDictionary[workerName]["class"](
            workerName,
            threadDictionary[workerName]["configuration"],
            cls.projectLogger)
        threadDictionary.pop(workerName)
        cls.projectWorker.registerMqttBridge(cls.projectMqttBridge)
        cls.projectWorker.startThread()

        for threadName in threadDictionary:
            thread = threadDictionary[threadName]["class"](
                threadName,
                threadDictionary[threadName]["configuration"],
                cls.projectLogger)
            thread.registerMqttBridge(cls.projectMqttBridge)
            thread.startThread()
        cls.projectThreads = threadDictionary       # remaining objects in threadDictionary are all just ordinary threads


    @classmethod
    def monitorThreads(cls, stopAfterSeconds : int):
        startTime = Supporter.getTimeStamp()
        running = True

        # loop until any thread throws an exception (and for debugging after 5 seconds)
        while (Base.ThreadInterface.ThreadInterface.getException() is None) and running:
            time.sleep(1)
            cls.projectLogger.trace(cls, "alive")
            cls.projectLogger.trace(cls, Supporter.encloseString(Base.ThreadInterface.ThreadInterface.getException(), ">>>>", "<<<<"))
            if stopAfterSeconds:
                if Supporter.getTimeStamp() - startTime > stopAfterSeconds:
                    running = False 

    @classmethod
    def createThreadDictionary(cls, configuration : dict):
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

                # filter special threads and store others in array so they can be set up in well known order independent from position in init file
                if issubclass(loadableClass, Logger.Logger.Logger):
                    # only one system wide Logger is allowed
                    if loggerName is None:
                        loggerName = threadName
                    else:
                        cls.raiseException("init file contains more than one Logger, at least [" + loggerName + "] and [" + threadName + "]")
                elif issubclass(loadableClass, MqttBridge.MqttBridge.MqttBridge):
                    # only one system wide MqttBridge is allowed
                    if mqttBridgeName is None:
                        mqttBridgeName = threadName
                    else:
                        cls.raiseException("init file contains more than one MqttBridge, at least [" + mqttBridgeName + "] and [" + threadName + "]")
                elif issubclass(loadableClass, Worker.Worker.Worker):
                    # only one system wide Worker is allowed
                    if workerName is None:
                        workerName = threadName
                    else:
                        cls.raiseException("init file contains more than one Worker, at least [" + workerName + "] and [" + threadName + "]")
                elif not issubclass(loadableClass, Base.ThreadInterface.ThreadInterface):
                    # init file error found
                    cls.raiseException("init file contained class [" + threadName + "] is not a sub class of [Base.ThreadInterface.ThreadInterface]")
                
                
                # since a json object is a dict each thread name is uniq (even if it isn't inside init file but duplicates will get lost!)
                threadDictionary[threadName] = { "class" : loadableClass, "configuration" : configuration[threadName] }
            else:
                cls.raiseException("definition " + threadName + " doesn't contain a \"class\" key")

        # ensure at least all necessary threads have been defined
        if loggerName is None:
            cls.raiseException("missing any Logger in init file")
        if mqttBridgeName is None:
            cls.raiseException("missing any MqttBridge in init file")
        if workerName is None:
            cls.raiseException("missing any Worker in init file")

        return (threadDictionary, loggerName, mqttBridgeName, workerName)


    @classmethod
    def executeProject(cls, initFileName : str, logLevel : Logger.Logger.Logger.LOG_LEVEL, stopAfterSeconds : int):
        '''
        Analyzes given init file and starts threds in well defined order

        It ensures that only one Logger thread, one MqttBridge thread and one Worker thread (or a subclass) has been defined.
        Logger will be executed first since all other threads need it for logging
        MqttBridge will be the second one since all other threads need it for inter-thread communication
        '''
        
        # ensure this method is called only once!
        if cls.executed:
            cls.raiseException("don't call executeProject() more than once")
        else:
            cls.executed = True

        Logger.Logger.Logger.setLogLevel(logLevel)

        configuration = cls.loadInitFile(initFileName)

        try:
            # validate init file content, load all classes and filter certain special classes (i.e. Logger, MqttBridge and Logger)
            (threadDictionary, loggerName, mqttBridgeName, workerName) = cls.createThreadDictionary(configuration)

            # now threads will be instantiated and stared, if any exception happens now we have to tear them down again!
            try:
                # now really setup all the threads
                #print(threadDictionary)
                cls.setupThreads(threadDictionary, loggerName, mqttBridgeName, workerName)
                cls.monitorThreads(stopAfterSeconds)        # "endless" while loop
            except Exception:
                print("INSTANTIATE EXCEPTION " + traceback.format_exc())
                #logging.exception("INSTANTIATE EXCEPTION " + traceback.format_exc())

            Base.ThreadInterface.ThreadInterface.stopAllWorkers()
        except Exception:
            print("SETUP EXCEPTION " + traceback.format_exc())
            #logging.exception("SETUP EXCEPTION " + traceback.format_exc())


