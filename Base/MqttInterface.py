from queue import Queue


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
        self.mqttRxQueue = Queue()      # set up  MQTT RX queue
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "MqttInterface init")


    def getRxQueue(self):
        '''
        Returns MQTT RX queue from whatever object has inherited from this class
        '''
        return self.mqttRxQueue

