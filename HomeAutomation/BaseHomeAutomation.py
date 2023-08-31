import Base.MqttBase


class BaseHomeAutomation(Base.MqttBase.MqttBase):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        '''
        pass


    @classmethod
    def getDiscoverySensorTopic(cls, deviceName, sensorName):
        pass

    @classmethod
    def getDiscoverySensorCmd(cls,  deviceName, sensorName, niceName = "", unit = "", subTopic = ""):
        pass

    @classmethod
    def getDiscoverySelectorTopic(cls, deviceName, sensorName):
        pass

    @classmethod
    def getDiscoverySelectorCmd(cls,  deviceName, optionList, niceName = ""):
        pass

    @classmethod
    def getDiscoveryInputNumberSliderTopic(cls, deviceName, sensorName):
        pass

    @classmethod
    def getDiscoveryInputNumberSliderCmd(cls,  deviceName, sensorName, niceName = "", minVal = 0, maxVal = 100):
        pass

    @classmethod
    def getDiscoverySwitchTopic(cls, deviceName, sensorName):
        pass

    @classmethod
    def getDiscoverySwitchCmd(cls,  deviceName, sensorName, niceName = ""):
        pass
    
    @classmethod
    def getDiscoverySwitchOptimisticStringCmd(cls,  deviceName, sensorName, onCmd, offCmd, niceName = ""):
        pass
