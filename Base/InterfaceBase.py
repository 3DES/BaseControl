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
        furthermore, because of performance reasons a proper self.inTopicOwnerDict has to be created in this method
        '''
        topic = self.getObjectTopic()
        inTopic = self.createInTopic(topic)
        self.inTopicOwnerDict = { inTopic : self.name }
        return [inTopic]


    def getOutTopicList(self):
        '''
        return a list with all out topics what usually is exactly one topic, but if an interface will provide more than one out topic it can overwrite this method, e.g. in the case of a RS485 bus with more than one device
        furthermore, because of performance reasons a proper self.outTopicOwnerDict has to be created in this method
        '''
        topic = self.getObjectTopic()
        outTopic = self.createOutTopic(topic)
        self.outTopicOwnerDict = { outTopic : self.name }
        return [outTopic]


    def getInTopicOwnerDict(self):
        '''
        return a dictionary containing in topics as keys and interface name as value, i.e. { inTopic : self.name }
        for performance reasons the dictionary should be created when self.getInTopicList() is called and if a child
        '''
        if not hasattr(self, 'inTopicOwnerDict'):
            self.getInTopicList()
        return self.inTopicOwnerDict


    def getOutTopicOwnerDict(self):
        '''
        return a dictionary containing out topics as keys and interface name as value, i.e. { outTopic : self.name }
        for performance reasons the dictionary should be created when self.getInTopicList() is called
        '''
        if not hasattr(self, 'outTopicOwnerDict'):
            self.getOutTopicList()
        return self.outTopicOwnerDict
