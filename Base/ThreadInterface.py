import threading
import traceback


from Base.MqttInterface import MqttInterface
import Logger          # prevent circular import!


class ThreadInterface(MqttInterface):
    '''
    classdocs
    '''


    threadLock = threading.Lock()   # class lock to access class variables

    setupThreadObjects = []         # all threads set up so far (even already teared down ones)
    exceptionThrown = None          # will be set with first thrown exception but not overwritten anymore
    setupThreads = 0                # threads setup counter (will no be decremented if a thread is teared down again, it's only incremented, so its sth. like an internal thread PID), threads should increment it and than store its content into object variable "self.threadNumber" 


    def __init__(self, threadName : str, configuration : dict, logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        # don't set up any further threads if there is already an exception!
        if self.exceptionThrown is None:
            self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "ThreadInterface init")
            self.event = threading.Event()
            self.thread = threading.Thread(target = self.threadLoop, args=[self.event])

            with self.threadLock:
                self.setupThreads += 1                      # ensure each thread has uniq number
                self.threadNumber = self.setupThreads       # remember own thread number
                self.setupThreadObjects.append(self)        # remember new thread in global thread list for tearing them all down if neccessary 
            self.thread.start()                             # finally start new thread
        else:
            self.logger.x(self.logger.LOG_LEVEL.FATAL, self.name, "exception seen from other thread, set up denied")


    def threadLoop(self, event):
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "starting thread loop (" + self.__class__.__name__ + ")")

        try:
            while not event.is_set():
                self.threadMethod()
                # do some overall thread related stuff here (@todo)
        except Exception as exception:
            with self.threadLock:
                self.exceptionThrown = exception

            self.logger.x(self.logger.LOG_LEVEL.FATAL, self.name, traceback.format_exc())

        self.tearDownMethod()


    def threadMethod(self):
        '''
        Thread method should not contain an endless loop
        
        To be overwritten in any case
        '''
        raise Exception("abstract method \"threadMethod()\" has to be overwritten by " + self.__class__.__name__)


    def tearDownMethod(self):
        '''
        Thread method called when a thread has been stopped via event
        
        To be overwritten if needed
        '''
        self.logger.x(self.logger.LOG_LEVEL.TRACE, self.name, "tear down method called")
        pass


    def stopThread(self):
        self.event.set()        # stop object thread via event
        return self.thread


    @classmethod
    def __stopAllWorkersLog(cls, loggerObject, level : int, sender : str, message : str):
        if loggerObject is not None:
            loggerObject.logger.x(level, sender, message)
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

        # stop workers first (so they can still log if necessary)
        for threadObject in reversed(cls.setupThreadObjects):
            if not isinstance(threadObject, Logger.Logger.Logger):
                cls.__stopAllWorkersLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.TRACE, cls.__name__, "tearing down object")
                thread = threadObject.stopThread()      # send stop to thread containing object and get real thread back
                threadsToJoin.append(thread)            # remember thread

        # join all stopped workers
        for thread in threadsToJoin:
            thread.join()                               # join all stopped threads

        # finally stop logger if available
        if tearDownLoggerObject is not None:
            cls.__stopAllWorkersLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.TRACE, cls.__name__, "tearing down logger")
            loggerThread = tearDownLoggerObject.stopThread()
            loggerThread.join()


