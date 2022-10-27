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
        self.objectList = None
        if "timeout" not in configuration:
            self.raiseException("WatchDog needs a timeout value in init file")
        configuration["timeout"] = int(configuration["timeout"])      # this will ensure that value contains a valid int even if it has been given as string (what is common in json!) 

        self.logger.info(self, "init (WatchDog)")


    def threadMethod(self):
        if self.objectList is None and (Supporter.getTimeStamp() - self.startupTime  > self.configuration["timeout"]):
            self.raiseException("no object list received within timeout time: " + str(self.configuration["timeout"]) + " seconds") 

        deltaTime = Supporter.getTimeStamp() - self.startupTime
        self.logger.warning(self, "objectList is set : " + str(self.objectList is not None) + " : " + str(self.configuration["timeout"]) + Supporter.encloseString(Supporter.getTimeStamp()) + Supporter.encloseString(self.startupTime) + Supporter.encloseString(str(deltaTime)))

        self.logger.trace(self, "I am the WatchDog thread")
        time.sleep(0.5)



