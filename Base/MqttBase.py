import time
import calendar
import json
import threading
import inspect
from enum import Enum
from queue import Queue
from strenum import StrEnum    # pip install StrEnum


from Base.Supporter import Supporter
from Base.InterfaceFactory import InterfaceFactory
import Base.ExtendedJsonParser
import Base.Base as Base


class MqttBase(Base.Base):
    '''
    classdocs
    '''
    __threadLock_always_use_getters_and_setters                 = threading.Lock()                                  # class lock to access class variables
    __exception_always_use_getters_and_setters                  = None                                              # will be set with first thrown exception but not overwritten anymore
    __mqttTxQueue_always_use_getters_and_setters                = Queue(Base.Base.QUEUE_SIZE + Base.Base.QUEUE_SIZE_EXTRA)    # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)
    __projectName_always_use_getters_and_setters                = None                                              # project name needed for MQTT's first level topic (i.e. <projectName>/<thread>/...)
    __watchDogMinimumTriggerTime_always_use_getters_and_setters = 0                                                 # project wide minimum watch dog time (if more than one watch dogs are running in the system the shortest time will be stored here!)
    __logger_always_use_getters_and_setters                     = None                                              # project wide logger
    __threadNames_always_use_getters_and_setters                = set()                                             # collect object names and ensure that they are all unique
    __mqttLock_always_use_getters_and_setters                   = threading.Lock()                                  # class lock to access class variables

    _CONTENT_TAG = "content"


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


    class MQTT_SUBTOPIC(StrEnum):
        TRIGGER_WATCHDOG      = 'watchdog'


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


    def mqttLocked(self):
        '''
        To test if the caller is the one that got the lock
        '''
        if not hasattr(self, '_semaphoreLocked'):
            self._semaphoreLocked = False
        return self._semaphoreLocked


    def mqttLock(self):
        '''
        To get the publish lock (reader/writer semaphore so that all writers are stopped when the reader wants to read)
        '''
        self._semaphore(True)
        self._semaphoreLocked = True


    def mqttUnlock(self):
        '''
        To release the publish lock (reader/writer semaphore so that all writers are stopped when the reader wants to read)
        '''
        self._semaphore(False)
        self._semaphoreLocked = False


    @classmethod
    def _semaphore(cls, lock : bool):
        '''
        the lock semaphore itself (reader/writer semaphore so that all writers are stopped when the reader wants to read)
        '''
        if lock:
            # try to get the semaphore, otherwise block
            MqttBase._MqttBase__mqttLock_always_use_getters_and_setters.acquire()
        else:
            # release the semaphore again
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


    def __init__(self, baseName : str, configuration : dict, interfaceQueues : dict = None, queueSize : int = Base.Base.QUEUE_SIZE):
        '''
        Constructor
        '''
        super().__init__(baseName, configuration)

        self.add_threadNames(baseName)                                      # add thread name to thread names list to ensure they are unique (add method checks this!)

        self.logger.info(self, "init (MqttBase)")
        self.startupTime = Supporter.getTimeStamp()                         # remember startup time
        self.watchDogTimer = Supporter.getTimeStamp()                       # remember time the watchdog has been contacted the last time, thread-wise!
        self.mqttRxQueue = Queue(queueSize)                                 # create RX MQTT listener queue

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
            self.interfaceInTopicOwner = {}
            self.interfaceOutTopicOwner = {}
            self.interfaceThreads = InterfaceFactory.createInterfaces(self.name, configuration["interfaces"])
            for interface in self.interfaceThreads:
                # get topic lists from interface
                inTopicList = interface.getInTopicList()
                outTopicList = interface.getOutTopicList()

                queue = None        # if no special interface queue given, published messages will be received via default queue
                # interface queue with key "None" will be used for all interfaces where not a dedicated queue has been given
                if (interfaceQueues is not None):
                    if interface in interfaceQueues:
                        # a dedicated queue has been given for current interface, so subscribe with this queue
                        queue = interfaceQueues[interface]
                    elif None in interfaceQueues:
                        # common queue for all interfaces has been given (key = None), so subscribe with this queue
                        queue = interfaceQueues[None]

                # remember topic lists and owner of topics
                for inTopic in inTopicList:
                    # ensure no in topic exists more than once
                    if inTopic in self.interfaceInTopics:
                        self.logger.error(self, f'in topic {inTopic} already exists in {self.name}')
                for outTopic in outTopicList:
                    # ensure no out topic exists more than once
                    if outTopic in self.interfaceOutTopics:
                        self.logger.error(self, f'out topic {outTopic} already exists in {self.name}')
                    # subscribe to OUT topic of this interface to receive messages
                    self.mqttSubscribeTopic(self.createOutTopicFilterFromOutTopic(outTopic), queue)

                self.interfaceInTopics += inTopicList                                    # add IN topics of this interface to send messages
                self.interfaceOutTopics += outTopicList                                  # add OUT topics of this interface to receive messages
                self.interfaceInTopicOwner.update(interface.getInTopicOwnerDict())      # add IN topic owners
                self.interfaceOutTopicOwner.update(interface.getOutTopicOwnerDict())    # add OUT topic owners


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


    def getObjectTopic(self, objectName = None, subTopic : str = None):
        '''
        Create object topic for current object or give object
        '''
        if objectName is None:
            return self.createProjectTopic(self.name, subTopic = subTopic)
        else:
            return self.createProjectTopic(objectName, subTopic = subTopic)


    def getClassTopic(self, subTopic : str = None):
        '''
        Create class topic for current object
        '''
        return self.createProjectTopic(self.__class__.__name__, subTopic)

    @classmethod
    def createProjectTopic(cls, objectName : str, subTopic : str = None):
        '''
        Creates a topic for given objectName, objectName should be a class name or a thread name or a interface name
        '''
        return cls.createSubTopic(cls.get_projectName() + "/" + objectName, subTopic)


    @classmethod
    def createInTopicFilter(cls, topic : str, subTopic : str = None):
        '''
        Create topic filter for IN messages to given topic and children
        '''
        return cls.createInTopic(topic, subTopic) + "/#"


    @classmethod
    def createInTopic(cls, topic : str, subTopic : str = None):
        '''
        Create topic for IN messages
        '''
        return cls.createSubTopic(topic + "/in", subTopic)


    @classmethod
    def createOutTopicFilterFromOutTopic(cls, topic : str):
        '''
        Create topic filter for OUT messages to given topic and children
        '''
        return topic + "/#"


    @classmethod
    def createOutTopicFilter(cls, topic : str, subTopic : str = None):
        '''
        Create topic filter for OUT messages to given topic and children
        '''
        return cls.createOutTopicFilterFromOutTopic(cls.createOutTopic(topic, subTopic))


    @classmethod
    def createSubTopic(cls, topic : str, subTopic : str = None):
        '''
        Create topic for OUT messages
        '''
        if (subTopic is None) or (not len(subTopic)):
            return topic
        else:
            return topic + "/" + str(subTopic)


    @classmethod
    def createOutTopic(cls, topic : str, subTopic : str = None):
        '''
        Create topic for OUT messages
        '''
        return cls.createSubTopic(topic + "/out", subTopic)


    def getTopicOwnerFromOutTopic(self, topic):
        if hasattr(self, 'interfaceOutTopicOwner') and topic in self.interfaceOutTopicOwner:
            return self.interfaceOutTopicOwner[topic]
        else:
            return None


    def getTopicOwnerFromInTopic(self, topic):
        if hasattr(self, 'interfaceInTopicOwner') and topic in self.interfaceInTopicOwner:
            return self.interfaceInTopicOwner[topic]
        else:
            return None


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


    def mqttPublish(self, topic : str, content, globalPublish : bool = True, enableEcho : bool = False, lock : bool = True):
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
                             content = content,
                             lock = lock)


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


    def mqttDiscoverySensor(self, sensors, ignoreKeys : list = None, nameDict : dict = None, unitDict : dict = None, subTopic : str = None, senderName : str = None) -> str:
        """
        sensors: dict, nestedDict oder List der Sensoren die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit einzelnen frindlyNames drin stehen
        unitDict: dict. Hier koennen einzelne keys mit einzelnen Einheiten drin stehen
        
        @return        created topic to which the sensor values have to be published to
        """
        senderObj = Supporter.getCaller()      # get caller object

        # nameDict is needed even if it hasn't been given
        if nameDict is None:
            nameDict = {}

        # default is is the name variable in the caller object if nth. else has been given
        if senderName is None:
            senderName = senderObj.name

        # create sensors out topic
        topic = self.createOutTopic(self.createProjectTopic(senderName), subTopic = subTopic)

        if type(sensors) == dict:
            nameList = []
            for key in sensors:
                # detect a nested dict
                if type(sensors[key]) == dict:
                    for nestedKey in sensors[key]:
                        nameList.append(f"{key}.{nestedKey}")
                        # check if key is a topic then extract threadname and create niceName with threadname and nested key
                        if "/" in key:
                            threadName = key.split("/")[1]
                            nameDict[f"{key}.{nestedKey}"] = f"{threadName} {nestedKey}"
                else:
                    nameList.append(key)
        else:
            nameList = sensors

        #Supporter.debugPrint(f"discover sensor called: [{senderName}] [{topic}] [{nameList}]", color = "blue")

        for key in nameList:
            niceName = ""
            unit = ""
            if (ignoreKeys is None) or (key not in ignoreKeys):
                if key in nameDict:
                    niceName = nameDict[key]
                if (unitDict is not None) and (key in unitDict):
                    unit = unitDict[key]
                preparedMsg = self.homeAutomation.getDiscoverySensorCmd(senderName, key, niceName, unit, topic)
                sensorTopic = self.homeAutomation.getDiscoverySensorTopic(senderName, key)
                senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)
        return topic


    def mqttDiscoveryText(self, textField, commandTopic : str = None, commandTemplate : str = None, stateTopic : str = None, valueTemplate : str = None, senderName : str = None) -> str:
        """
        textField: name of the text filed that has to be discovered
        ... @todo
        """
        senderObj = Supporter.getCaller()      # get caller object

        preparedMsg = {"name" : textField}
        if commandTopic is not None:
            preparedMsg["command_topic"] = commandTopic
        if commandTemplate is not None:
            preparedMsg["command_template"] = commandTemplate
        if stateTopic is not None:
            preparedMsg["state_topic"] = stateTopic
        if valueTemplate is not None:
            preparedMsg["value_template"] = valueTemplate
        #Supporter.debugPrint(f"{preparedMsg}", color = "LIGHTRED", borderSize = 5)
        #mosquitto_pub -t 'homeassistant/text/AccuTester_DEBUG_VariableName/config' -m '{"name" : "hallo", "command_topic" : "AccuTester/DEBUG/in", "command_template":"{ \"variable\" : \"{{ value }}\" }"}' -h homeassistant -u pi -P raspberry

        sensorTopic = self.homeAutomation.getDiscoveryTextTopic(senderName, textField)
        self.logger.debug(self, f"discover text message prepared: topic = {sensorTopic} content = {preparedMsg}")
        senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttUnDiscovery(self, sensor, senderName : str = None) -> str:
        """
        Remove a discovered element from MQTT broker

        sensor: single sensor to be reoved from MQTT broker and homeautomation
        """
        senderObj = Supporter.getCaller()      # get caller object

        # default is is the name variable in the caller object if nth. else has been given
        if senderName is None:
            senderName = senderObj.name

        sensorTopic = self.homeAutomation.getDiscoverySensorTopic(senderName, sensor)
        senderObj.mqttPublish(sensorTopic, "", globalPublish = True, enableEcho = False)


    def mqttDiscoveryInputNumberSlider(self, sensors, ignoreKeys : list = None, nameDict : dict = None, minValDict : dict = None, maxValDict : dict = None, stateTopics : dict = None, valueTemplates : dict = None):
        """
        sensors: dict oder List der Slider die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        minValDict: dict der minimal Slider Werte. default 0
        maxValDict: dict der maximal Slider Werte. default 100
        """
        senderObj = Supporter.getCaller()      # get caller object

        if type(sensors) == dict:
            nameList = list(sensors.keys())
        else:
            nameList = sensors
        sensorTopic = ""
        for key in nameList:
            niceName = ""
            minVal = 0
            maxVal = 100
            if (ignoreKeys is None) or (key not in ignoreKeys):
                if (nameDict is not None) and (key in nameDict):
                    niceName = nameDict[key]
                if (minValDict is not None) and (key in minValDict):
                    minVal = minValDict[key]
                if (maxValDict is not None) and (key in maxValDict):
                    maxVal = maxValDict[key]
                stateTopic    = stateTopics[key]    if stateTopics    and key in stateTopics    else None
                valueTemplate = valueTemplates[key] if valueTemplates and key in valueTemplates else None
                preparedMsg = self.homeAutomation.getDiscoveryInputNumberSliderCmd(senderObj.name, key, niceName, minVal, maxVal, stateTopic = stateTopic , valueTemplate = valueTemplate)
                sensorTopic = self.homeAutomation.getDiscoveryInputNumberSliderTopic(senderObj.name, key)
                senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttDiscoverySelector(self, sensors, ignoreKeys : list = None, niceName : str = ""):
        """
        sensors: dict oder List der optionen die zu auswaehlen angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        niceName: der Name des Selectors
        """
        senderObj = Supporter.getCaller()      # get caller object
        
        if type(sensors) == dict:
            nameList = list(sensors.keys())
        else:
            nameList = sensors
        nameListWithoutIgnoredOnes = []
        for item in nameList:
            if (ignoreKeys is None) or (item not in ignoreKeys):
                nameListWithoutIgnoredOnes.append(item)
        preparedMsg = self.homeAutomation.getDiscoverySelectorCmd(senderObj.name, nameListWithoutIgnoredOnes, niceName)
        sensorTopic = self.homeAutomation.getDiscoverySelectorTopic(senderObj.name, niceName.lower().replace(" ", "_"))
        senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttDiscoverySwitch(self, sensors, ignoreKeys : list = None, nameDict : dict = None, onCmd : str = "", offCmd : str = ""):
        """
        sensors: dict oder List der sensoren die angelegt werden sollen
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        """
        senderObj = Supporter.getCaller()      # get caller object

        if type(sensors) == dict:
            nameList = list(sensors.keys())
        else:
            nameList = sensors
        for key in nameList:
            niceName = ""
            if (ignoreKeys is None) or (key not in ignoreKeys):
                if (nameDict is not None) and (key in nameDict):
                    niceName = nameDict[key]
                if len(onCmd):
                    preparedMsg = self.homeAutomation.getDiscoverySwitchOptimisticStringCmd(senderObj.name, key, onCmd, offCmd, niceName)
                else:
                    preparedMsg = self.homeAutomation.getDiscoverySwitchCmd(senderObj.name, key, niceName)
                sensorTopic = self.homeAutomation.getDiscoverySwitchTopic(senderObj.name, key)
                if sensorTopic:
                    senderObj.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)


    def mqttSendPackage(self, mqttCommand : MQTT_TYPE, topic : str = None, content = None, incocnito : str = None, lock : bool = True):
        '''
        Universal send method to send all types of supported mqtt messages
        '''
        mqttMessageDict = {
            "sender"          : self.name if incocnito is None else incocnito,    # incocnito sending is usually only useful for testing system behavior!
            "command"         : mqttCommand,
            "topic"           : topic,  
            self._CONTENT_TAG : content,
            "timestamp"       : Supporter.getTimeStamp()
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

            if lock == self.mqttLocked():
                raise Exception(f"locking error: lock == mqttLocked() == {lock}, but they shouldn't be equal!")

            if lock:
                # barrier so all writers can be blocked by the one reader
                self.mqttLock()
                self.mqttUnlock()
            self.get_mqttTxQueue().put(mqttMessageDict, block = False)
        else:
            raise Exception(self.name + " tried to send invalid mqtt type: " + str(mqttMessageDict)) 


    def readMqttQueue(self, mqttQueue : Queue = None, convert : bool = True, error : bool = True, exception : bool = True, contentTag : str = None, information : str = None):
        '''
        Reads a message from given queue or from self.mqttRxQueue if no queue has been given
        Caller is responsible that queue is not empty when this method has been called

        @param queue        The queue the message should be read from, if not given self.mqttRxQueue will be used instead
        @param convert      If True it's expected that the read message contains a "content" key with a json string as value,
                            that json string will be converted into a dict and written back to "content" element
                            To be set to False in cases where non-json strings can be received
        @param error        If True an error will be written to logger
                            If False error -AND- exceptions are suppressed
        @param exception    If True an exception thrown by json.loads() will be thrown again,
                            in case of False the exception will be suppressed
        @param contentTag   Tag in message dict that contains json string that has to be converted
                            This is also the tag of the element that will be printed in debug case

        @return             received and maybe converted message will be given back to caller
        '''
        if mqttQueue is None:
            mqttQueue = self.mqttRxQueue

        if contentTag is None:
            contentTag = self._CONTENT_TAG

        message = mqttQueue.get(block = False)                                                  # read a message from queue
        infoText = '' if information is None else f" [{information}]"
        self.logger.debug(self, f"received message{infoText}: {message}")                       # debug message
        if convert:
            preString = message[contentTag]
            try:
                # @todo pruefen ob [contentTag] string enthaelt, falls Inhalt = dict, was dann?
                if self.name == "PowerPlant" and "schaltschwelle" in preString:
                    Supporter.debugPrint(f"pre :{preString}", color = "LIGHTRED", borderSize = 5)
                message[contentTag] = self.extendedJson.parse(message[contentTag])                           # try to convert content into dict
                #message[contentTag] = json.loads(message[contentTag])
                if self.name == "PowerPlant" and "schaltschwelle" in preString:
                    Supporter.debugPrint(f"post:{message[contentTag]}", color = "LIGHTBLUE", borderSize = 5)
            except Exception as ex:
                hexInfo = ""
                # filling hexInfo only works if content is of type str
                if type(message[contentTag]) == str:
                    hexInfo = '\n' + ' '.join(f'0x{ord(c):02x}' for c in message[contentTag])
                if error:
                    self.logger.error(self, f'Cannot convert content {preString} / {message[contentTag]} to python dict\n{ex})' + hexInfo)
                    if exception:
                        raise
                else:
                    self.logger.debug(self, f'Cannot convert content {preString} / {message[contentTag]} to python dict\n{ex}' + hexInfo)
                    if self.name == "PowerPlant" and "schaltschwelle" in preString:
                        Supporter.debugPrint(f"type:{type(preString)}", color = "LIGHTBLUE", borderSize = 5)
                        try:
                            Supporter.debugPrint(f"rep:{Base.ExtendedJsonParser.ExtendedJsonParser().parse(preString)}", color = "LIGHTBLUE", borderSize = 5)
                        except Exception as ex2:
                            Supporter.debugPrint(f"exc:{ex2}", color = "LIGHTBLUE", borderSize = 5)

        return message

