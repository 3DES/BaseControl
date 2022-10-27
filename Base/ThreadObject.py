'''
This is the main class for all threads except Logger!

Logger has to inherit from the parent of this class (ThreadInterface) to prevent circular imports
'''
from Logger.Logger import Logger
from Base.ThreadInterface import ThreadInterface


class ThreadObject(ThreadInterface):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        self.logger.info(self, "init (ThreadObject)")

