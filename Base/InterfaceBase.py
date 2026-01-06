from Base.ThreadObject import ThreadObject


class InterfaceBase(ThreadObject):
    '''
    classdocs
    '''

    MAX_INIT_TRIES = 50     # @TODO getter bauen

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.mqttSendWatchdogAliveMessage()     # send watch dog message immediately since interfaces can block


    def getInTopicList(self):
        '''
        return a list with all in topics what usually is exactly one topic, but if an interface will provide more than one in topic it can overwrite this method, e.g. in the case of a RS485 bus with more than one device
        '''
        topic = self.getObjectTopic()
        inTopic = self.createInTopic(topic)
        return [inTopic]


    def getOutTopicList(self):
        '''
        return a list with all out topics what usually is exactly one topic, but if an interface will provide more than one out topic it can overwrite this method, e.g. in the case of a RS485 bus with more than one device
        '''
        topic = self.getObjectTopic()
        outTopic = self.createOutTopic(topic)
        return [outTopic]
