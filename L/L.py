import time


from queue import Queue
from Base.SilentBase.TI import TI


class L(TI):
    '''
    classdocs
    '''


    __loggerQueue = Queue()


    @classmethod
    def x(cls, data : str):
        print("L.x() : " + data)
        # @todo write to queue


    def __init__(self, params):
        '''
        Constructor
        '''
        super().__init__(params)
        L.x("L")


    def threadMethod(self):
        print("new logger method")
        time.sleep(0.3)


