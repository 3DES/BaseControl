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

