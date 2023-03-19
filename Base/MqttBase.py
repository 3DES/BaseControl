import time
import calendar
import json
import threading
import inspect
from enum import Enum
from queue import Queue


from Base.Supporter import Supporter
from Base.InterfaceFactory import InterfaceFactory
from Base.Base import Base


class MqttBase(Base):
    '''
    classdocs
    '''
    __threadLock_always_use_getters_and_setters                 = threading.Lock()                                  # class lock to access class variables
    __exception_always_use_getters_and_setters                  = None                                              # will be set with first thrown exception but not overwritten anymore
    __mqttTxQueue_always_use_getters_and_setters                = Queue(Base.QUEUE_SIZE + Base.QUEUE_SIZE_EXTRA)    # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)
    __projectName_always_use_getters_and_setters                = None                                              # project name needed for MQTT's first level topic (i.e. <projectName>/<thread>/...)
    __watchDogMinimumTriggerTime_always_use_getters_and_setters = 0                                                 # project wide minimum watch dog time (if more than one watch dogs are running in the system the shortest time will be stored here!)
    __logger_always_use_getters_and_setters                     = None                                              # project wide logger
    __threadNames_always_use_getters_and_setters                = set()                                             # collect object names and ensure that they are all unique
    __mqttLock_always_use_getters_and_setters                   = threading.Lock()                                  # class lock to access class variables


    class MQTT_TYPE(Enum):
        CONNECT               = 0  # to register as listener own queue to MqttBridge 
        DISCONNECT            = 1  # will remove all subscriptions of the sender and the sender itself from listener list
        BROADCAST             = 2  # send broadcast message to all known listeners (independent from any subscriptions) 

        # PUBLISH  is the first type that needs a topic (this will be checked later, if you mess around with it please don't break it!)
        PUBLISH               = 3  # send message to all subscribers
        PUBLISH_LOCAL         = 4  # send message to local subscribers only
        PUBLISH_NO_ECHO       = 5  # send message to all subscribers but never back to the sender
        PUBLISH_LOCAL_NO_ECHO = 6  # send message to local subscribers only but never back to the sender

        # SUBSCRIBE is the first type that needs a topic filter (this will be checked later, if you mess around with it please don't break it!)
        SUBSCRIBE             = 7  # subscribe for local messages only, to un-subscribe use UNSUBSCRIBE
        UNSUBSCRIBE           = 8  # remove local and global subscriptions
        SUBSCRIBE_GLOBAL      = 9  # subscribe for local and global messages, to un-subscribe use UNSUBSCRIBE

    @classmethod
    def _illegal_call(cls):
        '''
        Can be called by any getters and setters that are not allowed to be called (e.g. for read only variables)
        Can even by used by sub-classes!
        '''
        raise Exception(inspect.stack()[1][3] + "() hasn't to be called!")


    @classmethod
    def get_threadLock(cls):
        '''
        Getter for __threadLock variable
        '''
        return MqttBase._MqttBase__threadLock_always_use_getters_and_setters


    @classmethod
    def set_threadLock(cls, lock : threading.Lock):
        '''
        Setter for __threadLock variable
        '''
        cls._illegal_call()


    @classmethod
    def mqttLock(cls):
        MqttBase._MqttBase__mqttLock_always_use_getters_and_setters.acquire()


    @classmethod
    def mqttUnlock(cls):
        MqttBase._MqttBase__mqttLock_always_use_getters_and_setters.release()


    @classmethod
    def get_threadNames(cls):
        '''
        Getter for __threadNames variable
        '''
        return MqttBase._MqttBase__threadNames_always_use_getters_and_setters


    @classmethod
    def add_threadNames(cls, threadName : str):
        '''
        Setter for __threadNames variable
        '''
        with cls.get_threadLock():
            if threadName in cls.get_threadNames():
                raise Exception("Object " + Supporter.encloseString(threadName) + " defined twice but they have to be unique, please fix init file")
            else:
                cls.get_threadNames().add(threadName)


    @classmethod
    def get_exception(cls):
        '''
        Getter for __exception variable
        '''
        return MqttBase._MqttBase__exception_always_use_getters_and_setters


    @classmethod
    def set_exception(cls, exception : Exception):
        '''
        Setter for __exception variable
        '''
        # only set first exception since that's the most interesting one!
        with cls.get_threadLock():
            if MqttBase._MqttBase__exception_always_use_getters_and_setters is None:
                MqttBase._MqttBase__exception_always_use_getters_and_setters = exception


    @classmethod
    def get_mqttTxQueue(cls):
        '''
        Getter for __mqttTxQueue variable
        '''
        return MqttBase._MqttBase__mqttTxQueue_always_use_getters_and_setters


    @classmethod
    def set_mqttTxQueue(cls, queue : Queue):
        '''
        Setter for __mqttTxQueue variable
        '''
        cls._illegal_call()


    @classmethod
    def get_logger(cls):
        '''
        Getter for __logger variable
        
        It's ok to use logger like "self.logger.info(...)" or so!
        '''
        return MqttBase._MqttBase__logger_always_use_getters_and_setters


    @classmethod
    def set_logger(cls, logger):
        '''
        Setter for __logger variable
        '''
        MqttBase._MqttBase__logger_always_use_getters_and_setters = logger
        MqttBase.logger = logger


    @classmethod
    def set_homeAutomation(cls, homeAutomation):

        #MqttBase._MqttBase__logger_always_use_getters_and_setters = logger
        MqttBase.homeAutomation = homeAutomation


    @classmethod
    def set_projectName(cls, projectName : str):
        '''
        Setter for __projectName
        '''
        with cls.get_threadLock():
            if MqttBase._MqttBase__projectName_always_use_getters_and_setters is None:
                MqttBase._MqttBase__projectName_always_use_getters_and_setters = projectName
            else:
                raise Exception("MqttBase's project name already set")


    @classmethod
    def get_projectName(cls):
        '''
        Getter for __projectName
        '''
        return MqttBase._MqttBase__projectName_always_use_getters_and_setters


    @classmethod
    def set_watchDogMinimumTime(cls, watchDogTime : int):
        '''
        Setter for __watchDogMinimumTime
        '''
        with cls.get_threadLock():
            if (MqttBase._MqttBase__watchDogMinimumTriggerTime_always_use_getters_and_setters == 0) or (MqttBase._MqttBase__watchDogMinimumTriggerTime_always_use_getters_and_setters > watchDogTime):
                MqttBase._MqttBase__watchDogMinimumTriggerTime_always_use_getters_and_setters = watchDogTime


    @classmethod
    def get_watchDogMinimumTriggerTime(cls):
        '''
        Getter for __watchDogMinimumTime
        '''
        return MqttBase._MqttBase__watchDogMinimumTriggerTime_always_use_getters_and_setters


    def tagsIncluded(self, tagNames : list, intIfy : bool = False, optional : bool = False, configuration : dict = None, default = None):
        '''
        Checks if given parameters are contained in task configuration
        
        A dictionary with configuration can be given optionally for the case that configuration has to be checked before super().__init__() has been called
        if intIfy is True it will be ensured that the value contains an integer
        if optional is True no exception will be thrown if element is missed, in that case the return value will be True if all given tags have been included or False if at least one wansn't included
        '''
        success = True

        # take given configuration or self.configuration, if none is available throw an exception
        if configuration is None:
            if not hasattr(self, "configuration"):
                raise Exception("tagsIncluded called without a configuration dictionary and without self.configuration set")
            else:
                configuration = self.configuration

        # check and prepare mandatory parameters
        for tagName in tagNames:
            if tagName not in configuration:
                # in case of not optional throw an exception
                if not optional:
                    raise Exception(self.name + " needs a \"" + tagName + "\" value in init file")

                # if there was only one element to check and it doesn't exist, set default value
                if len(tagNames) == 1:
                    configuration[tagName] = default
                success = False         # remember there was at least one missing element
            elif intIfy:
                configuration[tagName] = int(configuration[tagName])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        return success


    def __init__(self, baseName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(baseName, configuration)

        self.add_threadNames(baseName)                                      # add thread name to thread names list to ensure they are unique (add method checks this!)

        self.logger.info(self, "init (MqttBase)")
        self.startupTime = Supporter.getTimeStamp()                         # remember startup time
        self.watchDogTimer = Supporter.getTimeStamp()                       # remember time the watchdog has been contacted the last time, thread-wise!
        self.mqttRxQueue = Queue(self.QUEUE_SIZE)                           # create RX MQTT listener queue

        # thread topic handling
        self.objectTopic = self.getObjectTopic()                            # e.g. AccuControl/PowerPlant
        self.classTopic  = self.getClassTopic()                             # e.g. AccuControl/Worker
        self.watchDogTopic = self.createProjectTopic("WatchDog")            # each watch dog has to subscribe to that topic, without any exceptions!!!
        self.mqttConnect()                                                  # send connect message
        self.mqttSubscribeTopic(self.createInTopicFilter(self.objectTopic)) # subscribe to all topics with our name in it
        self.mqttSubscribeTopic(self.createInTopicFilter(self.classTopic))  # subscribe to all topics with our class in it

        self.interfaceQueues = interfaceQueues                              # remember interface queues, maybe we will need it later somewhere 

        if "interfaces" in configuration:
            self.interfaceInTopics = []
            self.interfaceOutTopics = []
            self.interfaceThreads = InterfaceFactory.createInterfaces(self.name, configuration["interfaces"])
            for interface in self.interfaceThreads:
                topic = interface.getObjectTopic()
                self.interfaceInTopics.append(self.createInTopic(topic))    # add IN topic of this interface to send messages
                self.interfaceOutTopics.append(self.createOutTopic(topic))  # add OUT topic of this interface to send messages
                if (interfaceQueues is not None) and (interface in interfaceQueues):
                    self.mqttSubscribeTopic(self.createOutTopicFilter(topic), queue = interfaceQueues[interface])   # subscribe to OUT topic of this interface to receive messages, since queues have been given use those one instead of default RX queue
                else:
                    self.mqttSubscribeTopic(self.createOutTopicFilter(topic))                                       # subscribe to OUT topic of this interface to receive messages


    @classmethod
    def raiseException(cls, message : str):
        '''
        Actually not in use, previously used to handle all exceptions at one place but now the exceptions are all caught by the threadLoop
        '''
        # create exception
        exception = Exception(message)

        # set first threads exception
        cls.set_exception(exception)

        # finally rise exception to let task come to an end
        raise exception


    def get_mqttListenerName(self):
        '''
        Return the name of this mqtt listener (usually it's self.name)
        '''
        return self.name


    @classmethod
    def simulateExcepitonError(self, name : str, value : int):
        '''
        To test if exceptions caught correctly
        just enter somewhere:
            MqttBase.simulateExcepitonError(self.name, 0)        # for immediate exception
            MqttBase.simulateExcepitonError(self.name, 10)       # for exception after 10 calls
        '''
        counterName = "__simulateExceptionError_" + name
        nameSpace = globals()
        if counterName not in nameSpace:
            nameSpace[counterName] = 1       # create local variable with name given in string
        else:
            nameSpace[counterName] += 1
        
        if nameSpace[counterName] >= value:
            raise Exception("testwise rissen exception : " + name)


    @classmethod
    def splitTopic(cls, topic : str):
        '''
        Unique split routine makes it easy to change split if necessary
        Splits topics as well as filters
        '''
        return topic.split("/")


    @classmethod
    def matchTopic(cls, topic : str, topicFilterLevels : list):
        '''
        Check if a topic filter matches a given topic
        It guesses that given topic filter and given topic are both valid
        
        Filter is expected as list (because of performance reasons filters usually are stored that way!)
        whereas topic usually is given as string

        Filters      possible tokens
        a         -> a
        a/b       -> a/b

        a/b/#     -> a/b, a/b/.+

        a/b/+     -> a/b/.+
        a/+/b     -> a/.+/b
        a/+/b/+/c -> a/.+/b/.+/c
        '''
        topicLevels       = cls.splitTopic(topic)

        maxIndex = len(topicFilterLevels)

        # last filter level is '#' so throw away all levels from topic behind that level and check only the ones before
        if topicFilterLevels[-1] == '#':
            maxIndex = len(topicFilterLevels) - 1

        # either the '#' wild card ensures that only up to maxIndex levels are to be compared or that the number of levels of topic filter and topic are identical
        # otherwise topic is too long for the filter or filter is too long for the topic, in both cases they will never match
        if (maxIndex == len(topicFilterLevels)):
            if (len(topicFilterLevels) != len(topicLevels)):
                return False
        else:
            if len(topicLevels) < maxIndex:
                return False

        # either a topic level is matched by '+' wild card or filter topic level element and topic level element are identical
        for index in range(maxIndex):
            if (topicFilterLevels[index] != '+') and (topicFilterLevels[index] != topicLevels[index]):
                return False

        return True


    @classmethod
    def validateTopicFilter(cls, topicFilter : str) -> bool:
        '''
        Validates a topic filter and returns the result
        '''
        topicLevels = cls.splitTopic(topicFilter)

        for index, level in enumerate(topicLevels):
            if len(level) == 0:                                     # topic was /xxx or xxx//xxx or xxx/ or empty (not valid according MQTT spec but mosquitto takes them)
                return False
            if (level == "#") and ((index + 1) < len(topicLevels)): # topic was xxx/#/xxx
                return False
            if len(level) > 1 and ('+' in level or '#' in level):   # topic was xxx/x+x or xxx/x#x
                return False

        return True


    @classmethod
    def validateTopic(cls, topic : str) -> bool:
        '''
        Validates a topic and returns the result
        '''
        topicLevels = cls.splitTopic(topic)

        for level in enumerate(topicLevels):
            if len(level) == 0:                                     # topic was /xxx or xxx//xxx or xxx/ or empty
                return False
            if '+' in level or '#' in level:                        # topic contained '+' or '#'
                return False

        return True


    def createTopic(self, classTopic : bool = False, inTopic : bool = False, filterTopic : bool = False):
        '''
        Create a topic type depending on given flags
        
        classTopic flag decides if a class or object topic will be created
        
        inTopic flag decides if a in or out topic will be created
        
        filterTopic flag decides if a common topic or a topic filter (/#) will be created
        '''
        if classTopic:
            topic = self.getClassTopic()
        else:
            topic = self.getObjectTopic()

        if filterTopic:
            if inTopic:
                topic = self.createInTopicFilter(topic)
            else:
                topic = self.createOutTopicFilter(topic)
        else:
            if inTopic:
                topic = self.createInTopic(topic)
            else:
                topic = self.createOutTopic(topic)
        return topic
        
    
    def getObjectTopic(self):
        '''
        Create object topic for current object
        '''
        return self.createProjectTopic(self.name)


    def getClassTopic(self):
        '''
        Create class topic for current object
        '''
        return self.createProjectTopic(self.__class__.__name__)

    @classmethod
    def createProjectTopic(cls, objectName : str):
        '''
        Creates a topic for given objectName, objectName should be a class name or a thread name or a interface name
        '''
        return cls.get_projectName() + "/" + objectName


    @classmethod
    def createInTopicFilter(cls, topic : str):
        '''
        Create topic filter for IN messages to given topic and children
        '''
        return cls.createInTopic(topic) + "/#"


    @classmethod
    def createInTopic(cls, topic : str):
        '''
        Create topic for IN messages
        '''
        return topic + "/in"


    @classmethod
    def createOutTopicFilter(cls, topic : str):
        '''
        Create topic filter for OUT messages to given topic and children
        '''
        return cls.createOutTopic(topic) + "/#"


    @classmethod
    def createOutTopic(cls, topic : str):
        '''
        Create topic for OUT messages
        '''
        return topic + "/out"


    @classmethod
    def createActualTopic(cls, topic : str):
        '''
        Create topic for actual messages
        '''
        return topic + "/out/actual"


    def mqttSubscribeTopic(self, topic : str, globalSubscription : bool = False, queue : Queue = None):
        '''
        Subscribe to a certain topic (locally OR globally)
        '''
        self.mqttSendPackage(MqttBase.MQTT_TYPE.SUBSCRIBE if not globalSubscription else MqttBase.MQTT_TYPE.SUBSCRIBE_GLOBAL,
                             topic = topic,
                             content = queue)


    def mqttUnSubscribeTopic(self, topic : str):
        '''
        Un-subscribe from a certain topic (locally AND globally)
        '''
        self.mqttSendPackage(MqttBase.MQTT_TYPE.UNSUBSCRIBE, topic = topic)


    def mqttConnect(self):
        '''
        Register as listener
        '''
        self.mqttSendPackage(MqttBase.MQTT_TYPE.CONNECT, content = self.mqttRxQueue)


    def mqttDisconnect(self):
        '''
        Unregister as listener
        '''
        self.mqttSendPackage(MqttBase.MQTT_TYPE.DISCONNECT)


    def mqttPublish(self, topic : str, content, globalPublish : bool = True, enableEcho : bool = False):
        '''
        Publish some message locally or globally
        If content is a dict, it's dumped to a string
        '''
        if type(content) == dict:
            # @todo ist das wirklich sinnvoll, was ist der genaue Grund und geht das evtl. irgendwie anders, so wird nur das dict gesondert behandelt!
            content = json.dumps(content)
        if enableEcho:
            messageType = MqttBase.MQTT_TYPE.PUBLISH if globalPublish else MqttBase.MQTT_TYPE.PUBLISH_LOCAL
        else:
            messageType = MqttBase.MQTT_TYPE.PUBLISH_NO_ECHO if globalPublish else MqttBase.MQTT_TYPE.PUBLISH_LOCAL_NO_ECHO
            
        self.mqttSendPackage(messageType,
                             topic = topic,
                             content = content)


    def watchDogTimeRemaining(self):
        '''
        Time in milliseconds that is remaining until watch dog has to be contacted for the next time
        If this value is negative watch dog already had to be informed
        
        In case self.get_watchDogMinimumTriggerTime() gives 0 the time has not yet set, therefore return a value > 0
        '''
        if self.get_watchDogMinimumTriggerTime():
            return self.get_watchDogMinimumTriggerTime() - (Supporter.getTimeStamp() - self.watchDogTimer)
        else:
            return 1


    def mqttSendWatchdogAliveMessage(self, content = None):
        '''
        Send alive message to watch dog
        '''
        self.watchDogTimer = Supporter.getTimeStamp()                               # reset watch dog time

        # init content if necessary
        if content is None:
            content = {}
        
        content["sender"] = self.name                                               # in any case set the sender here!

        self.mqttPublish(self.createInTopic(self.watchDogTopic), content, globalPublish = False)        # send alive message


    def mqttDiscoverySensor(self, senderObj, sensorList, ignoreKeys = [], nameDict = {}, unitDict = {}, topicAd = ""):
        """
        sensorList: dict oder List der Sensoren die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit einzelnen frindlyNames drin stehen
        unitDict: dict. Hier koennen einzelne keys mit einzelnen Einheiten drin stehen
        """
        if type(sensorList) == dict:
            nameList = list(sensorList.keys())
        else:
            nameList = sensorList
        for key in nameList:
            niceName = ""
            unit = ""
            if key not in ignoreKeys:
                if key in nameDict:
                    niceName = nameDict[key]
                if key in unitDict:
                    unit = unitDict[key]
                preparedMsg = self.homeAutomation.getDiscoverySensorCmd(senderObj.name, key, niceName, unit, topicAd)
                sensorTopic = self.homeAutomation.getDiscoverySensorTopic(senderObj.name, key)
                if sensorTopic:
                    senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttDiscoveryInputNumberSlider(self, senderObj, sensorList, ignoreKeys = [], nameDict = {}, minValDict = {}, maxValDict = {}):
        """
        sensorList: dict oder List der Slider die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        minValDict: dict der minimal Slider Werte. default 0
        maxValDict: dict der maximal Slider Werte. default 100
        """
        if type(sensorList) == dict:
            nameList = list(sensorList.keys())
        else:
            nameList = sensorList
        for key in nameList:
            niceName = ""
            minVal = 0
            maxVal = 100
            if key not in ignoreKeys:
                if key in nameDict:
                    niceName = nameDict[key]
                if key in minValDict:
                    minVal = minValDict["key"]
                if key in maxValDict:
                    maxVal = maxValDict["key"]
                preparedMsg = self.homeAutomation.getDiscoveryInputNumberSliderCmd(senderObj.name, key, niceName, minVal, maxVal)
                sensorTopic = self.homeAutomation.getDiscoveryInputNumberSliderTopic(senderObj.name, key)
                if sensorTopic:
                    senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttDiscoverySelector(self, senderObj, sensorList, ignoreKeys = [], niceName=""):
        """
        sensorList: dict oder List der optionen die zu auswaehlen angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        niceName: der Name des Selectors
        """
        if type(sensorList) == dict:
            nameList = list(sensorList.keys())
        else:
            nameList = sensorList
        nameListMinusIgnore = []
        for item in nameList:
            if item not in ignoreKeys:
                nameListMinusIgnore.append(item)
        preparedMsg = self.homeAutomation.getDiscoverySelectorCmd(senderObj.name, nameListMinusIgnore, niceName)
        sensorTopic = self.homeAutomation.getDiscoverySelectorTopic(senderObj.name, niceName.lower().replace(" ", "_"))
        if sensorTopic:
            senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttDiscoverySwitch(self, senderObj, sensorList, ignoreKeys = [], nameDict = {}):
        """
        sensorList: dict oder List der sensoren die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        """
        if type(sensorList) == dict:
            nameList = list(sensorList.keys())
        else:
            nameList = sensorList
        for key in nameList:
            niceName = ""
            if key not in ignoreKeys:
                if key in nameDict:
                    niceName = nameDict[key]
                preparedMsg = self.homeAutomation.getDiscoverySwitchCmd(senderObj.name, key, niceName)
                sensorTopic = self.homeAutomation.getDiscoverySwitchTopic(senderObj.name, key)
                if sensorTopic:
                    senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttSendPackage(self, mqttCommand : MQTT_TYPE, topic : str = None, content = None, incocnito : str = None):
        '''
        Universal send method to send all types of supported mqtt messages
        '''
        mqttMessageDict = {
            "sender"    : self.name if incocnito is None else incocnito,    # incocnito sending is usually only useful for testing system behavior!
            "command"   : mqttCommand,
            "topic"     : topic,  
            "content"   : content,
            "timestamp" : Supporter.getTimeStamp()
        }

        # validate mqttCommand
        if (mqttCommand.value >= MqttBase.MQTT_TYPE.CONNECT.value) and (mqttCommand.value <= MqttBase.MQTT_TYPE.SUBSCRIBE_GLOBAL.value):
            # validate topic if necessary
            if mqttCommand.value >= MqttBase.MQTT_TYPE.SUBSCRIBE.value:
                if not self.validateTopicFilter(topic):
                    raise Exception(self.name + " tried to send invalid topic filter : " + str(mqttMessageDict)) 
            elif mqttCommand.value >= MqttBase.MQTT_TYPE.PUBLISH.value:
                if not self.validateTopic(topic):
                    raise Exception(self.name + " tried to send invalid topic : " + str(mqttMessageDict)) 

            # barrier so all writers can be blocked by the one reader
            self.mqttLock()
            self.mqttUnlock()
            self.get_mqttTxQueue().put(mqttMessageDict, block = False)
        else:
            raise Exception(self.name + " tried to send invalid mqtt type: " + str(mqttMessageDict)) 

