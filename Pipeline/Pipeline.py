import time
from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class Pipeline(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.logger.info(self, "init (Pipeline)")


    def threadMethod(self):
        self.logger.trace(self, "Pipeline thread running")
        
        time.sleep(1)

