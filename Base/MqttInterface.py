import time
import calendar
import threading
from queue import Queue


from Base.Supporter import Supporter
#import Logger.Logger
#import MqttBridge.MqttBridge


class MqttInterface(object):
    '''
    classdocs
    '''


    # don't write class variables directly, ALWAYS use getters and setters!!!
    exception = None                # will be set with first thrown exception but not overwritten anymore

    mqttTxQueue = Queue()           # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)
    threadLock = threading.Lock()   # class lock to access class variables


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
    def setException(cls, exception : Exception):
        # if it's the first exception set it to class exception variable
        with cls.threadLock:
            if MqttInterface.exception is None:
                MqttInterface.exception = exception


    @classmethod
    def raiseException(cls, message : str):
        # create exception
        exception = Exception(message)

        cls.setException(exception)

        # finally rise exception to let task come to an end
        raise exception


    @classmethod
    def getException(cls) -> Exception:
        return MqttInterface.exception


    def getRxQueue(self):
        '''
        Returns MQTT RX queue from whatever object has inherited from this class
        '''
        return self.mqttRxQueue


    def registerMqttBridge(self, mqttBridge):
        if not hasattr(self, "mqttRxQueue"):
            self.mqttRxQueue = Queue()
        else:
            self.raiseException("object " + self.name + " has already registered to an MqttBridge")

        # whereas the transmit queue mqttTxQueue (TX Queue) is used by all threads the instance specific receive queue (RX Queue) has to be registered to the MqttBridge
        mqttBridge.addListener(self.name, self.mqttRxQueue)


