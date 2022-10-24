import threading
import time


from Base.SilentBase.MI import MI
import L


class TI(MI):
    '''
    classdocs
    '''


    workerThreadObjects = []        # all worker objects containing a thread
    overallRunning = False          # overall running flag set to be True when all workers have been set up
    workerThreadException = None


    def __init__(self, params):
        '''
        Constructor
        '''
        super().__init__(params)
        print("TI")
        L.L.L.x("xx")
        self.thread = threading.Thread(target = self.threadLoop)
        self.workerThreadObjects.append(self)
        self.thread.start()


    def threadLoop(self):
        '''
        Thread loop will wait for overallRunning becoming True and runs until overallRunning has been set to False again
        '''
        while not self.overallRunning:
            pass

        try:
            while (self.overallRunning):
                self.threadMethod()
                
                if self.workerThreadException is not None:
                    raise Exception("other worker thread threw an exception")
                
                # do some overall thread related stuff here
        except Exception as exception:
            if self.workerThreadException is None:
                self.workerThreadException = exception
            pass


    def threadMethod(self):
        '''
        Thread method should not contain an endless loop
        '''
        raise Exception("abstract method has to be overwritten")


    def stopThread(self):
        self.overallRunning = False
        return self.thread


    @classmethod
    def stopAllWorkers(cls):
        threadsToJoin = []
        loggerObject = None

        # stop workers first (so they can still log if necessary)
        for threadObject in cls.workerThreadObjects:
            if not isinstance(threadObject, L.L.L):
                thread = threadObject.stopThread()      # send stop to thread containing object and get real thread back
                threadsToJoin.append(thread)            # remember thread
            else:
                loggerObject = threadObject             # remember thread object of logger what has to be shut down at last

        # join all stopped workers
        for thread in threadsToJoin:
            thread.join()                               # join all stopped threads

        # finally stop logger if available
        if loggerObject is not None:
            logger = loggerObject.stopThread()
            logger.join()
