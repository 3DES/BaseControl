import time
from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class WatchDog(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, logger : Logger):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, logger)
        self.threadList = None
        if "timeout" not in configuration:
            raise Exception("WatchDog needs a timeout value in init file")    # self.raiseException
        configuration["timeout"] = int(configuration["timeout"])      # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        self.logger.info(self, "init (WatchDog)")


    def threadMethod(self):
        if self.threadList is None:
            raise Exception("no object list given")    # self.raiseException

        # @todo thread aufraeumen, hier ist im Moment alles nur Spielerei
        deltaTime = Supporter.getDeltaTime(self.startupTime)

        self.logger.trace(self, "WatchDog thread up since " + str(deltaTime) + " seconds = " + self.name)

        if Supporter.counter("watchDogMessage", 4, autoReset = True):
            Supporter.counter("watchDogMessageCounter", freeRunning = True);
            counter = Supporter.getCounterValue("watchDogMessageCounter");
            self.mqttPublish("WatchDog/request", "hello I'm the watch dog, sending message #" + str(counter))
            self.logger.debug(self, "sent message out to WatchDog/request, message #" + str(counter))

        self.logger.trace(self, "WatchDog thread up since " + str(deltaTime) + " seconds = " + self.name)
        
        time.sleep(0.5)


    def setThreadList(self, threadList : list):
        with self.get_threadLock():
            if self.threadList is None:
                self.threadList = threadList
            else:
                raise Exception("thread list already set")          # in "with" lock will be released automatically    # self.raiseException

