import time
import calendar
import threading
import inspect
from queue import Queue


from Base.Supporter import Supporter
#import Logger.Logger
#import MqttBridge.MqttBridge


class MqttInterface(object):
    '''
    classdocs
    '''


    __threadLock_always_use_getters_and_setters  = threading.Lock()     # class lock to access class variables
    __exception_always_use_getters_and_setters   = None                 # will be set with first thrown exception but not overwritten anymore
    __mqttTxQueue_always_use_getters_and_setters = Queue()              # the queue all tasks send messages to MqttBridge (MqttBridge will be the only one that reads form it!)


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
        # create exception
        exception = Exception(message)

        # set first threads exception
        cls.set_exception(exception)

        # finally rise exception to let task come to an end
        raise exception


    def get_mqttRxQueue(self):
        if not hasattr(self, "mqttRxQueue"):
            self.mqttRxQueue = Queue()
        else:
            self.raiseException("object " + self.name + " has already registered to an MqttBridge")
        return self.mqttRxQueue


    def get_mqttListenerName(self):
        return self.name

