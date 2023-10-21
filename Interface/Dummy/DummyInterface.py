import time


from Base.InterfaceBase import InterfaceBase


class DummyInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)


    #def threadInitMethod(self):
    #    pass


    def threadMethod(self):
        pass


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass
