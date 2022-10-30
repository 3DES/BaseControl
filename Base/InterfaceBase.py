import time
from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class InterfaceBase(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        