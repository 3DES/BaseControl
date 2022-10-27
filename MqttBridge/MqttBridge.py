import time
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttInterface import MqttInterface


class MqttBridge(ThreadObject):
    '''
    classdocs
    '''


    mqttListeners = None      # collect all listeners with their names and add topics if they subscribe for some or remove topics if they un-subscribe


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        if self.setMqttListenersList():
            super().__init__(threadName, configuration, logger)
            self.logger.info(self, "init (MqttBridge)")
        else:
            self.raiseException("MqttBridge already instantiated, no further instances allowed")


    @classmethod
    def setMqttListenersList(cls):
        '''
        Setter for cls.logQueue
        '''
        setupResult = False
        with cls.threadLock:
            if cls.mqttListeners is None:
                cls.mqttListeners = {}         # create listeners dictionary
                setupResult = True
        return setupResult


    def threadMethod(self):
        self.logger.trace(self, "I am the MqttBridge thread")
        time.sleep(1)


    @classmethod
    def addListener(cls, listenerName : str, listener : Queue):
        with cls.threadLock:
            if listenerName in cls.mqttListeners:
                cls.raiseException("listener " + listenerName + " already registered to MqttBridge")  
            cls.mqttListeners[listenerName] = { "queue" : listener , "subscriptions" : [] }

