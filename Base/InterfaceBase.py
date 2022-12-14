from Base.ThreadObject import ThreadObject


class InterfaceBase(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.mqttSendWatchdogAliveMessage()     # send watch dog message immediately since interfaces can block

