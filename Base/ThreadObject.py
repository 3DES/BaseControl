'''
This is the main class for all threads except Logger!

Logger has to inherit from the parent of this class (ThreadBase) to prevent circular imports
'''
from Logger.Logger import Logger
from Base.ThreadBase import ThreadBase


class ThreadObject(ThreadBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.logger.info(self, "init (ThreadObject)")

