import threading
import traceback


import Base.MqttInterface   # prevent circular import!
import Logger.Logger        # prevent circular import!
from Base.Supporter import Supporter 


class ThreadInterface(Base.MqttInterface.MqttInterface):
    '''
    classdocs
    '''


    setupThreadObjects = []         # all threads set up so far (even already teared down ones)
    numberOfThreads = 0             # threads setup counter (will no be decremented if a thread is teared down again, it's only incremented, so its sth. like an internal thread PID), threads should increment it and than store its content into object variable "self.threadNumber" 


    def __init__(self, threadName : str, configuration : dict, logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        # don't set up any further threads if there is already an exception!
        if self.exception is None:
            self.running = False
            
            self.logger.info(self, "init (ThreadInterface)")
            self.event = threading.Event()
            self.thread = threading.Thread(target = self.threadLoop, args=[self.event])

            self.threadNumber = self.addThread(self)
            self.thread.start()                             # finally start new thread
        else:
            self.logger.error(self, "exception seen from other thread, set up denied")


    @classmethod
    def addThread(cls, thread):
        '''
        Setter and getter for cls.numberOfThreads and cls.threadNumber
        '''
        with cls.threadLock:
            threadNumber = cls.numberOfThreads          # remember own thread number
            cls.numberOfThreads += 1                    # ensure each thread has uniq number
            cls.setupThreadObjects.append(thread)       # remember new thread in global thread list for tearing them all down if neccessary 
        return threadNumber


    def startThread(self):
        self.running = True


    def threadLoop(self, event):
        self.logger.trace(self, "thread loop started")

        try:
            while not self.running and not event.is_set():
                pass
            while self.running and not event.is_set():
                self.threadMethod()
                self.logger.debug(self, "alive")
                # do some overall thread related stuff here (@todo)
        except Exception as exception:
            # beside explicite exceptions handled tread internally we also have to catch all implicite exceptions
            self.setException(exception)

            self.logger.error(self, traceback.format_exc())

            self.logger.error(self, Supporter.encloseString(Base.ThreadInterface.ThreadInterface.getException(), "1>>>>", "<<<<"))
            self.logger.error(self, Supporter.encloseString(self.getException(), "2>>>>", "<<<<"))

        self.tearDownMethod()


    def threadMethod(self):
        '''
        Thread method should not contain an endless loop
        
        To be overwritten in any case
        '''
        self.raiseException("abstract method \"threadMethod()\" has to be overwritten by " + self.__class__.__name__)


    def tearDownMethod(self):
        '''
        Thread method called when a thread has been stopped via event
        
        To be overwritten if needed
        '''
        self.logger.info(self, "tear down method called")
        pass


    def stopThread(self):
        #elf.event.set()        # stop object thread via event
        self.running = False
        return self.thread


    @classmethod
    def __stopAllWorkersLog(cls, loggerObject, level : int, sender, message : str):
        if loggerObject is not None:
            loggerObject.message(level, sender, message)
        else:
            print("no logger found in tear down process: " + message)


    @classmethod
    def stopAllWorkers(cls):
        threadsToJoin = []

        # find Logger
        tearDownLoggerObject = None
        if len(cls.setupThreadObjects):
            tearDownLoggerObject = cls.setupThreadObjects[0]
            if not isinstance(tearDownLoggerObject.logger, Logger.Logger.Logger):
                tearDownLoggerObject = None

        # stop workers first but not the logger so we can still log if necessary
        for threadObject in reversed(cls.setupThreadObjects):
            if not isinstance(threadObject, Logger.Logger.Logger):
                cls.__stopAllWorkersLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down object " + Supporter.encloseString(threadObject.name))
                thread = threadObject.stopThread()      # send stop to thread containing object and get real thread back
                threadsToJoin.append(thread)            # remember thread

        # join all stopped workers
        for thread in threadsToJoin:
            thread.join()                               # join all stopped threads

        # finally stop logger if available
        if tearDownLoggerObject is not None:
            cls.__stopAllWorkersLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down logger " + Supporter.encloseString(tearDownLoggerObject.name))
            loggerThread = tearDownLoggerObject.stopThread()
            loggerThread.join()


