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
            self.raiseException("WatchDog needs a timeout value in init file")
        configuration["timeout"] = int(configuration["timeout"])      # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        self.logger.info(self, "init (WatchDog)")


    def threadMethod(self):
        if self.threadList is None:
            self.raiseException("no object list given")

        deltaTime = Supporter.getDeltaTime(self.startupTime)

        self.logger.trace(self, "WatchDog thread up since " + str(deltaTime) + " seconds")
        time.sleep(0.5)


    def setThreadList(self, threadList : list):
        with self.threadLock:
            if self.threadList is None:
                self.threadList = threadList
            else:
                self.raiseException("thread list already set")          # in "with" lock will be released automatically

