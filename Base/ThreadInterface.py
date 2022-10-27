import threading
import traceback
import time


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
            self.running = False        # to start thread until it's waiting endless
            self.killed  = False        # to stop thread independent if it has been started before or not
            
            self.logger.info(self, "init (ThreadInterface)")
            
            self.event = threading.Event()      # event is currently not used
            self.thread = threading.Thread(target = self.threadLoop, args=[self.event])

            self.threadNumber = self.addThread(self)        # register thread and receive uniq thread number (currently it's not used any further since all thread names are uniq, too)
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
        '''
        After a thread has been set up it will wait since some threads need to be further initialized
        When all necessary initialization and maybe synchronization has been done this method has to be called to make the thread running
        '''
        self.running = True


    def threadLoop(self, event):
        '''
        Thread loop started when thread is set up
        it will wait until xxx has been called and it will end when xxx has been called
        the method threadMethod() should not contain an endless loop since in that case overall monitoring and error handling will not work!

        Finally threadMethod() will be called to give the thread the possibility to clean up
        '''
        self.logger.trace(self, "thread loop started")

        # proces thread loop until thread gets killed
        try:
            # wait for getting started (or killed)
            while not self.running and not self.killed:     # and not event.is_set():
                time.sleep(0.1)    # be nice!

            # execute thread loop until we get killed
            while self.running and not self.killed:         # and not event.is_set():
                self.threadMethod()
                self.logger.debug(self, "alive")
                # do some overall thread related stuff here (@todo)
        except Exception as exception:
            # beside explicite exceptions handled tread internally we also have to catch all implicite exceptions
            self.setException(exception)
            self.logger.error(self, traceback.format_exc())

        # final thread clean up
        try:
            self.tearDownMethod()               # call tear down method for the case the thread has sth. to clean up
        except Exception as exception:
            # beside explicite exceptions handled tread internally we also have to catch all implicite exceptions
            self.setException(exception)
            self.logger.error(self, traceback.format_exc())

        self.logger.trace(self, "leaving thread loop")


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


    def killThread(self):
        '''
        Kill this thread
        '''
        #self.event.set()        # stop object thread via event
        self.killed = True
        return self.thread


    @classmethod
    def __stopAllThreadsLog(cls, loggerObject, level : int, sender, message : str):
        '''
        Logger wrapper since it could happen that the locker died and we cannot log anymore so we should at least print somethin
        '''
        if loggerObject is not None:
            loggerObject.message(level, sender, message)
        else:
            print("no logger found in tear down process: " + message)


    @classmethod
    def stopAllThreads(cls):
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
                cls.__stopAllThreadsLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down object " + Supporter.encloseString(threadObject.name))
                thread = threadObject.killThread()      # send stop to thread containing object and get real thread back
                threadsToJoin.append(thread)            # remember thread

        # join all stopped workers
        for thread in threadsToJoin:
            thread.join()                               # join all stopped threads

        # finally stop logger if available
        if tearDownLoggerObject is not None:
            cls.__stopAllThreadsLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down logger " + Supporter.encloseString(tearDownLoggerObject.name))
            loggerThread = tearDownLoggerObject.killThread()
            loggerThread.join()


