import time
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttBase import MqttBase
from Base.Supporter import Supporter
from pickle import TRUE


class MqttBridge(ThreadObject):
    '''
    classdocs
    '''


    __mqttListeners_always_use_getters_and_setters     = None       # collect queues and names of all registered listeners (this ensures MqttBridge is a singleton)
    __localSubscribers_always_use_getters_and_setters  = {}         # all subscriptions for local messages (all internal messages, even public published ones will be sent to these subscribers)
    __globalSubscribers_always_use_getters_and_setters = {}         # all subscriptions for global messages (all received from an external broker will be sent to these subscribers)


    @classmethod
    def setup_mqttListeners(cls):
        '''
        Setter for __mqttListeners
        Doesn't really needs a list but will just setup one and ensures this is done only once
        '''
        with cls.get_threadLock():
            if MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters is None:
                MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters = {}           # create listeners dictionary
            else:
                raise Exception("MqttBridge already instantiated, no further instances allowed")    # self.raiseException


    @classmethod
    def get_mqttListeners(cls) -> list:
        '''
        Getter for __mqttListeners
        '''
        return MqttBridge._MqttBridge__mqttListeners_always_use_getters_and_setters


    @classmethod
    def add_mqttListeners(cls, listenerName : str, listenerRxQueue : Queue):
        '''
        Add a listener to the listeners list
        Each mqtt listener has to register first before it can send subscribtions (for publishing only registering is not really necessary)
        '''
        # try to add new listener
        with cls.get_threadLock():
            if listenerName in cls.get_mqttListeners():
                raise Exception("listener " + listenerName + " already registered to MqttBridge")    # cls.raiseException
            cls.get_mqttListeners()[listenerName] = { "queue" : listenerRxQueue }


    @classmethod
    def remove_mqttListeners(cls, listenerName : str):
        '''
        Remove given listener from __mqttListeners
        '''
        with cls.get_threadLock():
            if listenerName not in cls.get_mqttListeners():
                raise Exception("listener " + listenerName + " is not registered to MqttBridge")    # cls.raiseException
            del(cls.get_mqttListeners()[listenerName])


    @classmethod
    def get_localSubscribers(cls) -> list:
        '''
        Getter for __localSubscribers
        '''
        return MqttBridge._MqttBridge__localSubscribers_always_use_getters_and_setters


    @classmethod
    def get_globalSubscribers(cls) -> list:
        '''
        Getter for __globalSubscribers
        '''
        return MqttBridge._MqttBridge__globalSubscribers_always_use_getters_and_setters


    def add_subscriber(self, subscriber : str, topicFilter : str, globalSubscription : bool = False):
        '''
        Add a subscriber to the local or global subscriber list
        '''
        if subscriber not in self.get_mqttListeners():
            raise Exception("subscriber is not a registered MQTT listener : " + str(subscriber))

        # select local or global subscriber list
        if globalSubscription:
            subscriberDict = self.get_globalSubscribers()
        else:
            subscriberDict = self.get_localSubscribers()

        # if the subscriber is not contained in subscriber list (i.e. first subscription) add a list for it first
        if subscriber not in subscriberDict:
            subscriberDict[subscriber] = []

        # validate and split topic filter        
        if not self.validateTopicFilter(topicFilter):
            raise Exception("invalid topic filter given: " + Supporter.encloseString(topicFilter, "\"", "\""))

        foundSubscription = False
        for subscription in subscriberDict[subscriber]:
            if "/".join(subscription) == topicFilter:   
                foundSubscription = True
                break

        # add split filter to subscriber list
        if not foundSubscription:
            topicFilterLevels = self.splitTopic(topicFilter)            # split filter topic for faster search
            subscriberDict[subscriber].append(topicFilterLevels)
            self.logger.info(self, Supporter.encloseString(subscriber) + " subscribed " + ("globally" if globalSubscription else "locally") + " for " + Supporter.encloseString(topicFilter))
        else:
            self.logger.debug(self, Supporter.encloseString(subscriber) + " already subscribed " + ("globally" if globalSubscription else "locally") + " for " + Supporter.encloseString(topicFilter))            


    def remove_subscriber(self, subscriber : str, topicFilter : str):
        '''
        Remove a subscriber from the local and global subscriber lists
        '''
        if subscriber not in self.get_mqttListeners():
            raise Exception("un-subscriber is not a registered MQTT listener : " + str(subscriber))

        # validate and split topic filter        
        if not self.validateTopicFilter(topicFilter):
            raise Exception("invalid topic filter given: " + Supporter.encloseString(topicFilter, "\"", "\""))

        unsubscribed = False

        # select local or global subscriber list
        for subscriberDict in (self.get_globalSubscribers(), self.get_localSubscribers()):
            if subscriber in subscriberDict:
                #newTopicsList = [topic for topic in subscriberDict[subscriber] if (topicFilter == "/".join(topic))]
                for index, topic in enumerate(subscriberDict[subscriber]):
                    checkTopic = "/".join(topic)
                    if topicFilter == checkTopic:
                        subscriberDict[subscriber].pop(index)
                        unsubscribed = True
                        break
                if not len(subscriberDict[subscriber]):
                    del(subscriberDict[subscriber])

        if not unsubscribed:
            self.logger.warning(self, Supporter.encloseString(subscriber) + " unsubscribed from not subscribed topic: " + Supporter.encloseString(topicFilter, "\"", "\""))
        else:
            self.logger.info(self, Supporter.encloseString(subscriber) + " unsubscribed from " + Supporter.encloseString(topicFilter))


    def disconnect_subscriber(self, subscriber : str):
        '''
        Remove a subscriber from the local and global subscriber lists
        '''
        if subscriber not in self.get_mqttListeners():
            raise Exception("un-subscriber is not a registered MQTT listener : " + str(subscriber))

        unsubscribed = False

        # select local or global subscriber list
        for subscriberDict in (self.get_globalSubscribers(), self.get_localSubscribers()):
            if subscriber in subscriberDict:
                del(subscriberDict[subscriber])
                unsubscribed = True

        # remove subscriber from listener list (so its queue is not known any longer!)
        self.remove_mqttListeners(subscriber)

        if not unsubscribed:
            self.logger.warning(self, Supporter.encloseString(subscriber) + " disconnected but haven't subscribed for anything so far")
        else:
            self.logger.info(self, Supporter.encloseString(subscriber) + " unsubscribed from all subscriptions")


    def publish_message(self, sender : str, topic : str, content : str, globalPublishing : bool = True):
        '''
        Usually a topic is published globally, if it is necessary that it's not sent out to the rest of the world it can be published locally, too
        '''
        # validate and split topic filter        
        if not self.validateTopic(topic):
            raise Exception("invalid topic given: " + Supporter.encloseString(topic, "\"", "\""))

        recipients = { sender }     # remember sender to prevent echoing

        # do we need global and local subscriber list or only local one?
        subscriberDictList = []
        if globalPublishing:
            subscriberDictList.append(self.get_globalSubscribers())
        subscriberDictList.append(self.get_localSubscribers())

        # handle lists now        
        for subscriberDict in subscriberDictList:
            # handle all subscribers
            for subscriber in subscriberDict:
                # ignore already informed subscribers
                if subscriber not in recipients:
                    for topicFilterLevels in subscriberDict[subscriber]:
                        # first matching filter stops handling of current subscriber
                        if self.matchTopic(topic, topicFilterLevels):
                            recipients.add(subscriber)
                            self.get_mqttListeners()[subscriber]["queue"].put({ "topic" : topic, "global" : globalPublishing, "content" : content }, block = False)
                            break


    def broadcast_message(self, sender : str, content : str):
        '''
        This kind of message will be sent to any known listeners
        '''
        # add global and local subscriber list into a set with unique elements and remove the sender
        subscriberSet = set(list(self.get_globalSubscribers()))
        subscriberSet.update(set(list(self.get_localSubscribers())))
        subscriberSet.remove(sender)

        for subscriber in subscriberSet:
            self.get_mqttListeners()[subscriber]["queue"].put(content, block = False)


    def __init__(self, threadName : str, configuration : dict):
        self.setup_mqttListeners()
        super().__init__(threadName, configuration)
        self.logger.info(self, "init (MqttBridge)")


    def threadMethod(self):
        '''
        MqttBridge worker method executed periodically from ThreadBase.threadLoop()
        '''
        self.logger.trace(self, "I am the MqttBridge thread = " + self.name)

        # first of all handle the system wide TX Queue where MqttBridge is the only reader
        while not self.get_mqttTxQueue().empty():
            newMqttMessageDict = self.get_mqttTxQueue().get(block = False)      # read a message

            # log received message in a more readable form
            newMqttMessage = "message received: sender=" + newMqttMessageDict["sender"] + " type=" + str(newMqttMessageDict["command"])
            if newMqttMessageDict["topic"] is not None:
                newMqttMessage += " topic=" + newMqttMessageDict["topic"] 
            if newMqttMessageDict["content"] is not None:
                newMqttMessage += " content=" + Supporter.encloseString(newMqttMessageDict["content"], "\"", "\"")

            self.logger.debug(self, newMqttMessage)

            # handle type of received message
            if newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.CONNECT.value:
                # "sender" is the sender's name
                # "content" has to be a queue.Queue here!
                self.add_mqttListeners(newMqttMessageDict["sender"], newMqttMessageDict["content"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.DISCONNECT.value:
                # "sender" is the sender's name
                self.disconnect_subscriber(newMqttMessageDict["sender"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.BROADCAST.value:
                # "sender" is the sender's name
                # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                self.broadcast_message(newMqttMessageDict["sender"], newMqttMessageDict["content"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.PUBLISH.value:
                # "sender" is the sender's name
                # "topic"  is a string containing the topic 
                # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.PUBLISH_LOCAL.value:
                # "sender" is the sender's name
                # "topic"  is a string containing the topic 
                # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"], globalPublishing = False)
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.SUBSCRIBE.value:
                # "sender" is the sender's name
                # "topic"  is a string containing the topic filter 
                self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.UNSUBSCRIBE.value:
                # "sender" is the sender's name
                # "topic"  is a string containing the topic filter 
                self.remove_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"])
            elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.SUBSCRIBE_GLOBAL.value:
                # "sender" is the sender's name
                # "topic"  is a string containing the topic filter 
                self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], globalSubscription = True)
            else:
                raise Exception("unknown type found in message " + str(newMqttMessageDict))


    #def threadBreak(self):
    #    pass
