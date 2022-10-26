import time
from queue import Queue


from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Base.MqttInterface import MqttInterface


class MqttBridge(ThreadObject):
    '''
    classdocs
    '''


    mqttListenersDictionary = None      # collect all listeners with their names and add topics if they subscribe for some or remove toppics if they unsubscribe


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        if MqttBridge.mqttListenersDictionary is None:
            MqttBridge.mqttListenersDictionary = {}
            super().__init__(threadName, configuration, logger)
            self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "MqttBridge init")
        else:
            logger.x(logger.LOG_LEVEL.FATAL, threadName, "MqttBridge already instantiated, no further instance allowed")
            raise Exception("MqttBridge already instantiated, no further instance allowed")


    def threadMethod(self):
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "I am MqttBridge thread")
        time.sleep(1)


    def addListener(self, listener : MqttInterface):
        pass
        
        