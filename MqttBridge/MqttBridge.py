import time
import re
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttBase import MqttBase
from Base.Supporter import Supporter


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
                raise Exception("MqttBridge already instantiated, no further instances allowed")


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
                raise Exception("listener " + listenerName + " already registered to MqttBridge")
            cls.get_mqttListeners()[listenerName] = { "queue" : listenerRxQueue }


    @classmethod
    def remove_mqttListeners(cls, listenerName : str):
        '''
        Remove given listener from __mqttListeners
        '''
        with cls.get_threadLock():
            if listenerName not in cls.get_mqttListeners():
                raise Exception("listener " + listenerName + " is not registered to MqttBridge")
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


    def add_subscriber(self, subscriber : str, topicFilter : str, globalSubscription : bool = False, queue : Queue = None):
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
            subscriberDict[subscriber].append({
                "topicFilter": topicFilterLevels,
                "queue"      : queue,
            })
            self.logger.info(self, Supporter.encloseString(subscriber) + " subscribed " + ("globally" if globalSubscription else "locally") + " for " + Supporter.encloseString(topicFilter))
        else:
            self.logger.warning(self, Supporter.encloseString(subscriber) + " already subscribed " + ("globally" if globalSubscription else "locally") + " for " + Supporter.encloseString(topicFilter))            


    def remove_subscriber(self, subscriber : str, topicFilter : str):
        '''
        Remove a subscriber from the local and global subscriber lists
        '''
        def unsubscribe(subscriber : str, topicFilter : str, subscriptions : dict) -> bool:
            '''
            Tries to find given subscriber in given subscriber dictionary
            '''
            unsubscribed = False
            if subscriber in subscriptions:
                #newTopicsList = [topic for topic in subscriptions[subscriber] if (topicFilter == "/".join(topic))]
                for index, topicAndQueue in enumerate(subscriptions[subscriber]):
                    topic = topicAndQueue["topicFilter"]
                    checkTopic = "/".join(topic)        # since the topic parts are stored in split form they have to be joined before they can be compared
                    if topicFilter == checkTopic:
                        subscriptions[subscriber].pop(index)
                        unsubscribed = True
                        break   # subscription found, leave search loop
                if not len(subscriptions[subscriber]):
                    del(subscriptions[subscriber])
            return unsubscribed
            
        if subscriber not in self.get_mqttListeners():
            raise Exception("un-subscriber is not a registered MQTT listener : " + str(subscriber))

        # validate and split topic filter        
        if not self.validateTopicFilter(topicFilter):
            raise Exception("invalid topic filter given: " + Supporter.encloseString(topicFilter, "\"", "\""))

        unsubscribedGlobally = unsubscribe(subscriber, topicFilter, self.get_globalSubscribers())
        unsubscribedLocally  = unsubscribe(subscriber, topicFilter, self.get_localSubscribers())

        if not unsubscribedLocally and not unsubscribedGlobally:
            self.logger.warning(self, Supporter.encloseString(subscriber) + " tried to unsubscribe from not subscribed topic: " + Supporter.encloseString(topicFilter, "\"", "\""))
        else:
            unsubscribeText = ""
            if unsubscribedGlobally:
                unsubscribeText += "globally"
            if unsubscribedLocally:
                if unsubscribedGlobally:
                    unsubscribeText += " and "
                unsubscribeText += "locally"
            self.logger.info(self, f"{Supporter.encloseString(subscriber)} unsubscribed {unsubscribeText} from {Supporter.encloseString(topicFilter)}")


    def disconnect_subscriber(self, subscriber : str):
        '''
        Remove a subscriber from the local and the global subscriber lists
        '''
        if subscriber not in self.get_mqttListeners():
            raise Exception("un-subscriber is not a registered MQTT listener : " + str(subscriber))

        unsubscribed = False

        # remove subscriber from global and local list
        for subscriberDict in (self.get_globalSubscribers(), self.get_localSubscribers()):
            if subscriber in subscriberDict:
                del(subscriberDict[subscriber])
                unsubscribed = True

        # remove subscriber from listeners list (so its queue is not known any longer!)
        self.remove_mqttListeners(subscriber)

        if not unsubscribed:
            self.logger.warning(self, Supporter.encloseString(subscriber) + " disconnected but haven't subscribed for anything so far")
        else:
            self.logger.info(self, Supporter.encloseString(subscriber) + " unsubscribed from all subscriptions")


    def publish_message(self, sender : str, topic : str, content : str, globalPublishing : bool = True, enableEcho : bool = False):
        '''
        Usually a topic is published globally, if it is necessary that it's not sent out to the rest of the world it can be published locally, too
        The globalPublishing flag in each messages allows a global subscriber to check if the message is a local or a global one 
        '''
        # validate and split topic filter        
        if not self.validateTopic(topic):
            raise Exception("invalid topic given: " + Supporter.encloseString(topic, "\"", "\""))

        handledRecipients = set()         # never send a message twice to one and the same recipient

        if not enableEcho:
            handledRecipients.add(sender)

        subscriberDictList = []
        if globalPublishing:
            # global subscribers receive global messages
            subscriberDictList.append(self.get_globalSubscribers())
        else:
            # local subscribers receive local messages
            subscriberDictList.append(self.get_localSubscribers())

        # handle lists now        
        for subscriberDict in subscriberDictList:
            # handle all subscribers
            for subscriber in subscriberDict:
                # ignore already informed subscribers
                if subscriber not in handledRecipients:
                    for topicAndQueue in subscriberDict[subscriber]:
                        topicFilterLevels = topicAndQueue["topicFilter"]
                        # first matching filter stops handling of current subscriber
                        if self.matchTopic(topic, topicFilterLevels):
                            handledRecipients.add(subscriber)
                            try:
                                if topicAndQueue["queue"] is not None:
                                    # subscriber subscribed with special queue so send it to this one instead of using the default one
                                    topicAndQueue["queue"].put({ "topic" : topic, "global" : globalPublishing, "content" : content }, block = False)
                                else:
                                    # no special queue for this subscription so send it to the default one
                                    self.get_mqttListeners()[subscriber]["queue"].put({ "topic" : topic, "global" : globalPublishing, "content" : content }, block = False)
                                break
                            except Exception as ex:
                                # probably any full queue!
                                raise Exception(f"{self.name} : {subscriber} {self.get_mqttListeners()[subscriber]['queue'].qsize()}\ncaught exception:{ex}")


    def broadcast_message(self, sender : str, content : str):
        '''
        This kind of message will be sent to any known listeners
        '''
        # @todo das braucht vermutlich niemand... ersatzweise waere ein Broadcast topic zu ueberlegen, auf das jeder Interessierte subscribed...
        # add global and local subscriber list into a set with unique elements and remove the sender
        subscriberSet = set(list(self.get_globalSubscribers()))
        subscriberSet.update(set(list(self.get_localSubscribers())))
        subscriberSet.remove(sender)

        for subscriber in subscriberSet:
            self.get_mqttListeners()[subscriber]["queue"].put(content, block = False)


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        self.setup_mqttListeners()
        super().__init__(threadName, configuration, interfaceQueues)
        self.logger.info(self, "init (MqttBridge)")


    def threadInitMethod(self):
        self.removeMqttRxQueue()        # mqttRxQueue not needed so remove it


    turn  = 0
    def threadMethod(self):
        '''
        MqttBridge worker method executed periodically from ThreadBase.threadLoop()
        '''
        threadLoopStartTime = Supporter.getTimeStamp()      # meassure time inside loop
        messageCounter = 0                                  # count messages handled in current loop run
        # first of all handle the system wide TX Queue where MqttBridge is the only reader

        try:
            self.mqttLock()
            self.logger.debug(self, f"lock queue")
            while not self.get_mqttTxQueue().empty():
                messageCounter += 1
                self.turn += 1
                # self.logger.info(self, f"{messageCounter} {self.turn} {self.get_mqttTxQueue().qsize()}")
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
                    self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"], enableEcho = True)
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.PUBLISH_LOCAL.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic
                    # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                    self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"], globalPublishing = False, enableEcho = True)
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.PUBLISH_NO_ECHO.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic 
                    # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                    self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"])
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.PUBLISH_LOCAL_NO_ECHO.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic
                    # "content" is the message that will be sent out to anybody else (in case of messages sent to the outer world the MqttInterace has to convert not string/int stuff into string stuff since nobody outside the project can handle our Queues or so!)
                    self.publish_message(newMqttMessageDict["sender"], newMqttMessageDict["topic"], newMqttMessageDict["content"], globalPublishing = False)
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.SUBSCRIBE.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic filter
                    self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], queue = newMqttMessageDict["content"])
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.UNSUBSCRIBE.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic filter
                    self.remove_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"])
                elif newMqttMessageDict["command"].value == MqttBase.MQTT_TYPE.SUBSCRIBE_GLOBAL.value:
                    # "sender" is the sender's name
                    # "topic"  is a string containing the topic filter
                    self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], queue = newMqttMessageDict["content"], globalSubscription = True)
                    self.add_subscriber(newMqttMessageDict["sender"], newMqttMessageDict["topic"], queue = newMqttMessageDict["content"])                                  # global subscribers subscribe for local and global list
                else:
                    raise Exception("unknown type found in message " + str(newMqttMessageDict))

                if Supporter.getSecondsSince(threadLoopStartTime) > 20:
                    self.logger.info(self, f"Thread loop took more than 20 seconds, last command was: {newMqttMessageDict['command'].value}, messages handled: {messageCounter}")
                    break
        finally:
            self.logger.debug(self, f"unlock queue")
            self.mqttUnlock()

    #def threadBreak(self):
    #    pass
