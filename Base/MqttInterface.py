import time
import calendar
import threading
import inspect
from enum import Enum
from queue import Queue


from Base.Supporter import Supporter
from _ast import Or
from pip._vendor.distlib.util import OR
from win32evtlogutil import langid
from _operator import or_
from json.decoder import _decode_uXXXX
#import Logger.Logger
#import MqttBridge.MqttBridge


class MqttInterface(object):
    '''
    classdocs
    '''


    __threadLock_always_use_getters_and_setters  = threading.Lock()     # class lock to access class variables
    __exception_always_use_getters_and_setters   = None                 # will be set with first thrown exception but not overwritten anymore
    __mqttTxQueue_always_use_getters_and_setters = Queue(100)           # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)


    class MQTT_TYPE(Enum):
        DISCONNECT         = 0  # will remove all subscriptions of the sender

        PUBLISH            = 1  # send message to all subscribers
        PUBLISH_LOCAL      = 2  # send message to local subscribers only

        SUBSCRIBE          = 3  # subscribe for local messages only, to un-subscribe use UNSUBSCRIBE
        UNSUBSCRIBE        = 4  # remove local and global subscriptions
        SUBSCRIBE_GLOBAL   = 5  # subscribe for local and global messages, to un-subscribe use UNSUBSCRIBE


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
        return MqttInterface._MqttInterface__threadLock_always_use_getters_and_setters


    @classmethod
    def set_threadLock(cls, lock : threading.Lock):
        '''
        Setter for __threadLock variable
        '''
        cls._illegal_call()


    @classmethod
    def get_exception(cls):
        '''
        Getter for __exception variable
        '''
        return MqttInterface._MqttInterface__exception_always_use_getters_and_setters


    @classmethod
    def set_exception(cls, exception : Exception):
        '''
        Setter for __exception variable
        '''
        # only set first exception since that's the most interesting one!
        with cls.get_threadLock():
            if MqttInterface._MqttInterface__exception_always_use_getters_and_setters is None:
                MqttInterface._MqttInterface__exception_always_use_getters_and_setters = exception


    @classmethod
    def get_mqttTxQueue(cls):
        '''
        Getter for __mqttTxQueue variable
        '''
        return MqttInterface._MqttInterface__mqttTxQueue_always_use_getters_and_setters


    @classmethod
    def set_mqttTxQueue(cls, queue : Queue):
        '''
        Setter for __mqttTxQueue variable
        '''
        cls._illegal_call()


    def __init__(self, baseName : str, configuration : dict, logger):
        '''
        Constructor
        '''
        super().__init__()
        self.name = baseName
        self.configuration = configuration
        self.logger = logger
        self.logger.info(self, "init (MqttInterface)")
        self.startupTime = Supporter.getTimeStamp()


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


    def get_mqttRxQueue(self):
        '''
        Return object mqtt Queue but has to be called once by MqttBridge where this thread is connected to, a thread itself can directly use it via "self.mqttRxQueue"
        
        There are two queues for mqtt:
        - one class wide mqttTxQueue only read by the singleton MqttBridge but written by all MqttInterfaces
        - one mqttRxQueue per instance only written by the MqttBridge and read only by its owner instance 
        '''
        if not hasattr(self, "mqttRxQueue"):
            self.mqttRxQueue = Queue(100)
        else:
            raise Exception("object " + self.name + " has already registered to an MqttBridge")    # self.raiseException
        return self.mqttRxQueue


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
            MqttInterface.simulateExcepitonError(self.name, 0)        # for immediate exception
            MqttInterface.simulateExcepitonError(self.name, 10)       # for exception after 10 calls
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

        for index, level in enumerate(topicLevels):
            if len(level) == 0:                                     # topic was /xxx or xxx//xxx or xxx/ or empty
                return False
            if '+' in level or '#' in level:                        # topic contained '+' or '#'
                return False

        return True


    def mqttSubscribeTopic(self, topic : str, globalSubscription : bool = False):
        '''
        Subscribe to a certain topic (locally OR globally)
        '''
        self.mqttSendPackage(MqttInterface.MQTT_TYPE.SUBSCRIBE if not globalSubscription else MqttInterface.MQTT_TYPE.SUBSCRIBE_GLOBAL,
                             topic = topic)


    def mqttUnSubscribeTopic(self, topic : str):
        '''
        Un-subscribe from a certain topic (locally AND globally)
        '''
        self.mqttSendPackage(MqttInterface.MQTT_TYPE.UNSUBSCRIBE, topic = topic)


    def mqttDisconnect(self):
        '''
        Un-subscribe from a certain topic (locally AND globally)
        '''
        self.mqttSendPackage(MqttInterface.MQTT_TYPE.DISCONNECT)


    def mqttPublish(self, topic : str, content : str, globalPublish : bool = True):
        '''
        Publish some message locally or globally
        '''
        self.mqttSendPackage(MqttInterface.MQTT_TYPE.PUBLISH if globalPublish else MqttInterface.MQTT_TYPE.PUBLISH_LOCAL,
                             topic = topic,
                             content = content)
        

    def mqttSendPackage(self, mqttType : MQTT_TYPE, topic : str = None, content : str = None):
        '''
        Universal send method to send all types of supported mqtt messages
        '''
        mqttMessageDict = {
            "sender"  : self.name,
            "type"    : mqttType,
            "topic"   : topic,  
            "content" : content
        }

        # validate mqttType
        if (mqttType.value >= MqttInterface.MQTT_TYPE.DISCONNECT.value) and (mqttType.value <= MqttInterface.MQTT_TYPE.SUBSCRIBE_GLOBAL.value):
            # validate topic if necessary
            if mqttType.value >= MqttInterface.MQTT_TYPE.SUBSCRIBE.value:
                if not self.validateTopicFilter(topic):
                    raise Exception(self.name + " tried to send invalid topic filter : " + str(mqttMessageDict)) 
            elif mqttType.value >= MqttInterface.MQTT_TYPE.PUBLISH.value:
                if not self.validateTopic(topic):
                    raise Exception(self.name + " tried to send invalid topic : " + str(mqttMessageDict)) 

            self.get_mqttTxQueue().put(mqttMessageDict, block = False)
        else:
            raise Exception(self.name + " tried to send invalid mqtt type: " + str(mqttMessageDict)) 

