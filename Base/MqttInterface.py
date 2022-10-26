from queue import Queue


#import Logger.Logger
#import MqttBridge.MqttBridge


class MqttInterface(object):
    '''
    classdocs
    '''


    mqttTxQueue = Queue()       # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)


    def __init__(self, baseName : str, configuration : dict, logger):
        '''
        Constructor
        '''
        super().__init__()
        self.name = baseName
        self.logger = logger
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "MqttInterface init")


    def getRxQueue(self):
        '''
        Returns MQTT RX queue from whatever object has inherited from this class
        '''
        return self.mqttRxQueue


    def registerMqttBridge(self, mqttBridge):
        if not hasattr(self, "mqttRxQueue"):
            self.mqttRxQueue = Queue()
        else:
            raise Exception("object " + self.name + " has already registered to an MqttBridge")
        
        # whereas the transmit queue mqttTxQueue (TX Queue) is used by all threads the instance specific receive queue (RX Queue) has to be registered to the MqttBridge
        mqttBridge.addListener(self.name, self.mqttRxQueue)


