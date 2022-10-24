from L.L import L
from Base.SilentBase.TI import TI


class T(TI):
    '''
    classdocs
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        super().__init__(params)
        L.x("T " + self.name)
