import time
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttInterface import MqttInterface


class MqttBridge(ThreadObject):
    '''
    classdocs
    '''


    __mqttListeners_always_use_getters_and_setters = None      # collect all listeners with their names and add topics if they subscribe for some or remove topics if they un-subscribe


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

    
    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        self.setup_mqttListeners()
        super().__init__(threadName, configuration, logger)
        self.logger.info(self, "init (MqttBridge)")


    def threadMethod(self):
        self.logger.trace(self, "I am the MqttBridge thread = " + self.name)

        while not self.get_mqttTxQueue().empty():
            newMqttMessage = self.get_logQueue().get(block = False)
            self.add_logMessage("message received : " + newMqttMessage)

        time.sleep(1)

