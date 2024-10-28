'''
This is the main class for all threads except Logger!

Logger has to inherit from the parent of this class (ThreadBase) to prevent circular imports
'''
from Logger.Logger import Logger
from Base.ThreadBase import ThreadBase
import Base.Base as Base


class ThreadObject(ThreadBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None, queueSize : int = Base.Base.QUEUE_SIZE):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues, queueSize)
        self.logger.info(self, "init (ThreadObject)")

