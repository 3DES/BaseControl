import time
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttInterface import MqttInterface
from Base.Supporter import Supporter


class MqttBridge(ThreadObject):
    '''
    classdocs
    '''


    __mqttListeners_always_use_getters_and_setters     = None       # collect all listeners with their names and add topics if they subscribe for some or remove topics if they un-subscribe
    __localSubscribers_always_use_getters_and_setters  = {}         # all subscriptions for local messages
    __globalSubscribers_always_use_getters_and_setters = {}         # all subscriptions for global messages


    @classmethod
    def setup_mqttListeners(cls):
        '''
        Setter for __mqttListeners
        Doesn't really needs a list but will just setup one and ensures this is done only once
        '''
        with cls.get_threadLock():
            if MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters is None:
                MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters = {}         # create listeners dictionary
            else:
                raise Exception("MqttBridge already instantiated, no further instances allowed")    # self.raiseException

    
    @classmethod
    def get_mqttListeners(cls) -> list:
        '''
        Getter for __mqttListeners
        '''
        return MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters


    @classmethod
    def add_mqttListeners(cls, listener : MqttInterface):
        # get necessary listener information
        listenerName = listener.get_mqttListenerName()
        listenerRxQueue = listener.get_mqttRxQueue()
        
        # try to add new listener
        with cls.get_threadLock():
            if listenerName in cls.get_mqttListeners():
                raise Exception("listener " + listenerName + " already registered to MqttBridge")    # cls.raiseException
            cls.get_mqttListeners()[listenerName] = { "queue" : listenerRxQueue , "subscriptions" : [] }

    
    @classmethod
    def get_localSubscribers(cls) -> list:
        '''
        Getter for __mqttListeners
        '''
        return MqttBridge._MqttBridge__localSubscribers_always_use_getters_and_setters

    
    @classmethod
    def get_globalSubscribers(cls) -> list:
        '''
        Getter for __mqttListeners
        '''
        return MqttBridge._MqttBridge__globalSubscribers_always_use_getters_and_setters


    def add_subscriber(self, subscriber : str, topicFilter : str, globalSubscription : bool = False):
        if subscriber not in self.get_mqttListeners():
            raise Exception("subscriber is not a registered MQTT listener : " + str(subscriber))

        if globalSubscription:
            subscriberDict = self.get_globalSubscribers()
        else:
            subscriberDict = self.get_localSubscribers()

        if subscriber not in subscriberDict:
            subscriberDict[subscriber] = []

        # validate and split topic filter        
        self.validateTopicFilter(topicFilter)
        topicFilterLevels = self.splitTopic(topicFilter)
        
        # add split filter to subscriber list
        subscriberDict[subscriber].append(topicFilterLevels)
        
        self.logger.info(self, Supporter.encloseString(subscriber) + " subscribed " + ("globally" if globalSubscription else "locally") + " for " + Supporter.encloseString(topicFilter))
        

    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        self.setup_mqttListeners()
        super().__init__(threadName, configuration, logger)
        self.logger.info(self, "init (MqttBridge)")


    def threadMethod(self):
        self.logger.trace(self, "I am the MqttBridge thread = " + self.name)

        while not self.get_mqttTxQueue().empty():
            newMqttMessageDict = self.get_mqttTxQueue().get(block = False)
            newMqttMessage = "message received: sender=" + newMqttMessageDict["sender"] + " type=" + str(newMqttMessageDict["type"])
            if newMqttMessageDict["topic"] is not None:
                newMqttMessage += " topic=" + newMqttMessageDict["topic"] 
            if newMqttMessageDict["content"] is not None:
                newMqttMessage += " content=" + Supporter.encloseString(newMqttMessageDict["content"], "\"", "\"")

            self.logger.debug(self, newMqttMessage)

            if newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.CONNECT.value:
                pass
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.DISCONNECT.value:
                pass
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.PUBLISH.value:
                pass
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.PUBLISH_LOCAL.value:
                pass
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.SUBSCRIBE.value:
                self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], False)
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.UNSUBSCRIBE.value:
                pass
            elif newMqttMessageDict["type"].value == MqttInterface.MQTT_TYPE.SUBSCRIBE_GLOBAL.value:
                self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], True)
            else:
                raise Exception("unknown type found in message " + str(newMqttMessageDict))

        time.sleep(1)

