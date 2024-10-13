import threading
import traceback
import time


import Base
import Logger.Logger        # prevent circular import!
import Base.MqttBase        # prevent circular import!
from Base.Supporter import Supporter 


class ThreadBase(Base.MqttBase.MqttBase):
    '''
    classdocs
    '''


    __setupThreadObjects_always_use_getters_and_setters = []         # all threads set up so far (even already teared down ones)
    __numberOfThreads_always_use_getters_and_setters    = 0          # threads setup counter (will no be decremented if a thread is teared down again, it's only incremented, so its sth. like an internal thread PID), threads should increment it and than store its content into object variable "self.threadNumber" 
    threadStarted = False  # thread not yet started (will be set to True in method that can be overwritten if some initialization has to be done before other threads are allowed to start)


    @classmethod
    def get_setupThreadObjects(cls):
        '''
        Getter for __setupThreadObjects variable
        '''
        return ThreadBase._ThreadBase__setupThreadObjects_always_use_getters_and_setters

    
    @classmethod
    def add_setupThreadObjects(cls, thread):
        '''
        Setter for __setupThreadObjects variable
        '''
        cls.get_setupThreadObjects().append(thread)


    @classmethod
    def get_numberOfThreads(cls):
        '''
        Getter for __numberOfThreads variable
        '''
        return ThreadBase._ThreadBase__numberOfThreads_always_use_getters_and_setters


    @classmethod
    def set_numberOfThreads(cls, numberOfThreads : int):
        '''
        Setter for __numberOfThreads variable
        '''
        ThreadBase._ThreadBase__numberOfThreads_always_use_getters_and_setters = numberOfThreads


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)
        # don't set up any further threads if there is already an exception!
        if self.get_exception() is None:
            self.killed  = False        # to stop thread independent if it has been started before or not

            self.logger.info(self, "init (ThreadBase)")

            self.event = threading.Event()                  # event is currently not used
            self.thread = threading.Thread(target = self.threadLoop, args=[self.event], daemon = True)

            self.interfaceThreads = None                    # to collect interfaces setup during thread init phase

            self.threadNumber = self.addThread(self)        # register thread and receive uniq thread number (currently it's not used any further since all thread names are uniq, too)
        else:
            self.logger.error(self, "exception seen from other thread, set up denied")


    @classmethod
    def addThread(cls, thread) -> int:
        '''
        Adds a thread to __setupThreadObjects and increments __numberOfThreads
        '''
        with cls.get_threadLock():
            threadNumber = cls.get_numberOfThreads()    # remember own thread number
            cls.set_numberOfThreads(threadNumber + 1)   # ensure each thread has unique number
            cls.add_setupThreadObjects(thread)          # remember new thread in global thread list for tearing them all down if necessary 
        return threadNumber


    def start(self):
        self.thread.start()                             # finally start all thread interfaces and the new thread


    def mqttRxQueueEmptyDecorator(self, functionToDecorate):
        def mqttRxQueueEmptyMonitor(*args, **kwargs):
            returnValue = functionToDecorate(*args, **kwargs)
            self._mqttRxQueueEmptyWasTrue = returnValue
            #Supporter.debugPrint(f"{self.name} self.mqttRxQueue.empty wrapper called")
            return returnValue
        return mqttRxQueueEmptyMonitor


    def installMqttRxQueueEmptyMonitor(self):
        self.mqttRxQueue.empty = self.mqttRxQueueEmptyDecorator(self.mqttRxQueue.empty)
        self.logger.debug(self, f"installed self.mqttRxQueue.empty monitor")


    def removeMqttRxQueue(self):
        '''
        Threads that don't need a mqttRxQueue should call this method to remove it since ThreadBase checks if it has been read each time threadMethod is called and if it hasn't been read an exception will be thrown
        '''
        del self.mqttRxQueue


    def threadBreak(self):
        '''
        This is to ensure that each thread has at least a little sleep per loop run

        If the thread wants to handle this by itself it has to overwrite this method
        '''
        time.sleep(.1)          # give other threads a chance to run and ensure that a thread which writes to the logger doesn't flood it


    def threadRxQueueMonitor(self):
        # check if threadMethod handled mqttRxQueue correctly, what means it has to do one of the following three options:
        #     - it read the queue until empty returned with True
        #     - it set self._mqttRxQueueGetIgnoreOnce
        #     - it has deleted its queue completely (usually with the helper function self.removeMqttRxQueue())
        if not self._mqttRxQueueEmptyWasTrue and not self._mqttRxQueueGetIgnoreOnce and hasattr(self, "mqttRxQueue"):
            # thread doesn't read its mqttRxQueue, so let's check if anybody sends stuff to it
            if not self.mqttRxQueue.empty():
                while not self.mqttRxQueue.empty():
                    self.logger.debug(self, f"is not reading its mqttRxQueue but anybody sends to it: {self.mqttRxQueue.get()}")
            raise Exception(f"{self.name}({self.__class__.__name__}) hasn't called self.mqttRxQueue.get() or self.mqttRxQueue.empty() and got True, what is not allowed! Either delete self.mqttRxQueue or set self._mqttRxQueueGetIgnoreOnce to True each time it cannot be read")


    def threadLoop(self, event):
        '''
        Thread loop started when thread is set up, it will run until self.killed becomes True
        the method threadMethod() should not contain an endless loop since in that case overall monitoring and error handling will not work!

        Finally threadTearDownMethod() will be called to give the thread the possibility to clean up
        '''
        self.logger.trace(self, "thread loop started")

        self.setThreadStarted()      # signalize that thread has been started

        # first of all execute thread init method once
        try:
            self.threadInitMethod()             # call init method for the case the thread has sth. to set up
            self.threadSimmulationSupport()     # checks if simulation mode is supported in case "SIMULATE" flag has been set in init file, has to be overwritten by every thread and interface that supports simulation mode since otherwise SIMULATE flag cause an exception!
        except Exception as exception:
            # beside explicitly exceptions handled tread-internally we also have to catch all implicit exceptions
            self.set_exception(exception)
            self.logger.error(self, traceback.format_exc())

        #timeStamps = [[0, 0, 0, 0, 0], None]

        loopCount = 0

        # maybe mqttRxQueue has been deleted in threadInitMethod?
        if hasattr(self, "mqttRxQueue"):
            self.installMqttRxQueueEmptyMonitor()
        else:
            self.logger.debug(self, f"didn't install self.mqttRxQueue.empty monitor since self.mqttRxQueue has already been removed")


        # execute thread loop until thread gets killed
        try:
            # execute thread loop until we get killed
            while not self.killed:              # and not event.is_set():
                loopCount += 1

                #timeStamps[1] = timeStamps[0]
                #timeStamps[0] = [0, 0, 0, 0, 0]
                #timeStamps[0][0] = Supporter.getTimeStamp()            # remember current start time
                self.threadTraceMethod()        # print tracing info
                #timeStamps[0][1] = Supporter.getTimeStamp()            # time before thread main loop starts

                self._mqttRxQueueEmptyWasTrue = False   # reset monitoring variable
                self._mqttRxQueueGetIgnoreOnce = False  # to be set in threadMethod if the queue cannot be read temporarily

                self.threadMethod()             # execute working method
                self.threadRxQueueMonitor()     # check if mqttRxQueue has been handled as expected

                #timeStamps[0][2] = Supporter.getTimeStamp()            # time before thread main loop has been finished (delta is loop time)
                self.logger.debug(self, "alive")
                # do some overall thread related stuff here (@todo)

                self.threadWatchdogTrigger()
                #timeStamps[0][3] = Supporter.getTimeStamp()            # time after watchdog has been triggered

                time.sleep(0.05)
                self.threadBreak()              # be nice!
                #timeStamps[0][4] = Supporter.getTimeStamp()

                #self.logger.trace(self, f"loop turn: {loopCount}, duration: {timeStamps[0][4] - timeStamps[0][0]}s, delta since last start: {timeStamps[0][0] - timeStamps[1][0]}, turns {loopCount}")

        except Exception as exception:
            # beside explicite exceptions handled thread-internally we also have to catch all implicit exceptions
            self.set_exception(exception)
            self.logger.error(self, traceback.format_exc())

        # final thread clean up
        try:
            #self.logger.info(self, f"timing of last turn: {'/'.join(str(timeStamp) for timeStamp in timeStamps[0])} :: {'/'.join(str(timeStamp) for timeStamp in timeStamps[1])}")
            self.threadTearDownMethod()                             # call tear down method for the case the thread has sth. to clean up

            # stop interfaces after own tear down method since the tear down method could need the interface!
            if self.interfaceThreads is not None:
                for interface in self.interfaceThreads:                    
                    interfaceThread = interface.killThread()        # send stop to thread containing object and get real thread back
                for interface in self.interfaceThreads:
                    interfaceThread.join(Base.Base.Base.JOIN_TIME)  # join all stopped threads
        except Exception as exception:
            # beside explicite exceptions handled tread-internally we also have to catch all implicit exceptions
            self.set_exception(exception)
            self.logger.error(self, traceback.format_exc())

        self.logger.trace(self, "leaving thread loop")


    def threadWatchdogTrigger(self):
        '''
        Triggers Watchdog but should be overwritten if necessary
        '''
        if self.watchDogTimeRemaining() <= 0:
            self.mqttSendWatchdogAliveMessage()


    def setThreadStarted(self):
        '''
        Simply sets start flag so that project start up routine knows that the next thread can be started
        
        It's possible to overwrite this method and set just a pass in it so the variable self.threadStarted
        can be set somewhere else if a thread needs some time for start up before others are allowed to start.
        Usually that's necessary if some initialization cannot be done in __init__() but has to be done in
        threadInitMethod() since __init__() is executed during setup but threadInitMethod() is not called
        before the thread has been started
        '''
        self.threadStarted = True


    def threadInitializationFinished(self):
        '''
        To check if setup has been done and e.g. next thread can be started
        '''
        return self.threadStarted


    def threadInitMethod(self):
        '''
        Will be called once when thread loop is started
        
        Should be overwritten when needed
        '''
        self.logger.info(self, "thread init method called")


    def threadSimmulationSupport(self):
        '''
        To be overwritten in case thread or interface supports SIMULATE flag
        otherwise SIMULATE flag is not allowed to be set!
        '''
        if self.toSimulate():
            raise Exception(f"{self.name}: SIMULATE not yet implemented") 


    def threadTraceMethod(self):
        self.logger.trace(self, self.name + " : loop turn")


    def threadMethod(self):
        '''
        Thread method should not contain an endless loop
        
        To be overwritten in any case
        '''
        self.logger.info(self, "thread method called, should be overwritten")


    def threadTearDownMethod(self):
        '''
        Thread method called when a thread has been stopped via event
        
        To be overwritten if needed
        '''
        self.logger.info(self, "thread tear down method called")


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
        Logger wrapper since it could happen that the locker died and we cannot log anymore so we should at least print something
        '''
        if loggerObject is not None:
            loggerObject.message(level, sender, message)
        else:
            Logger.Logger.Logger.message(level, sender, message)


    @classmethod
    def stopAllThreads(cls):
        threadsToJoin = {}

        # find Logger
        tearDownLoggerObject = None
        if len(cls.get_setupThreadObjects()):
            tearDownLoggerObject = cls.get_setupThreadObjects()[0]
            if not isinstance(tearDownLoggerObject.logger, Logger.Logger.Logger):
                tearDownLoggerObject = None

        # stop workers first but not the logger so we can still log if necessary
        for threadObject in reversed(cls.get_setupThreadObjects()):
            if not isinstance(threadObject, Logger.Logger.Logger):
                cls.__stopAllThreadsLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down object " + Supporter.encloseString(threadObject.name))
                thread = threadObject.killThread()          # send stop to thread containing object and get real thread back
                threadsToJoin[threadObject.name]= thread    # remember thread

        # join all stopped workers
        for thread,threadObject in sorted(threadsToJoin.items()):
            # @todo eigentlich sollte nicht Logger.Logger.Logger.message verwendet werden sondern Logger.Logger.Logger.get_logger().message!!! Das gilt systemweit!!!
            Logger.Logger.Logger.message(Logger.Logger.Logger.LOG_LEVEL.INFO, cls, f"joining {thread}")
            threadObject.join(Base.Base.Base.JOIN_TIME)     # join all stopped threads
            time.sleep(0)                                   # give the logger task the chance to clear its queue content

        # finally stop logger if available
        if tearDownLoggerObject is not None:
            Supporter.debugPrint(f"tearing down {Supporter.encloseString(tearDownLoggerObject.name)}", borderSize = 0)
            cls.__stopAllThreadsLog(tearDownLoggerObject, Logger.Logger.Logger.LOG_LEVEL.INFO, cls, "tearing down logger " + Supporter.encloseString(tearDownLoggerObject.name))
            loggerThread = tearDownLoggerObject.killThread()
            Supporter.debugPrint(f"joining {Supporter.encloseString(tearDownLoggerObject.name)}", borderSize = 0)
            loggerThread.join(Base.Base.Base.JOIN_TIME)     # finally join the logger thread

