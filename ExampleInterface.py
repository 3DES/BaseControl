import time


from Base.InterfaceBase import InterfaceBase


class ExampleInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        #self.removeMqttRxQueue()        # mqttRxQueue has to be removed if it's not needed!
        
        #if not self.tagsIncluded(["optionalTag"], intIfy = True, optional = True):
        #    self.configuration["optionalTag"] = 10     # default value if not given, 10 is great

        #self.tagsIncluded(["mandatoryTag1", "mandatoryTag2", "mandatoryTag3"])


    #def threadInitMethod(self):
    #    pass


    def threadMethod(self):
        pass


    #def threadBreak(self):
    #    pass


    #def threadTraceMethod(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass
