import time
from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class WatchDog(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        # check and prepare mandatory parameters 
        if "triggerTime" not in configuration:
            raise Exception("WatchDog needs a \"triggerTime\" value in init file")      # self.raiseException
        configuration["triggerTime"] = int(configuration["triggerTime"])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        if "timeout" not in configuration:
            raise Exception("WatchDog needs a \"timeout\" value in init file")          # self.raiseException
        configuration["timeout"] = int(configuration["timeout"])                        # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        if "numberOfThreads" not in configuration:
            raise Exception("WatchDog needs a \"numberOfThreads\" value in init file")  # self.raiseException
        configuration["numberOfThreads"] = int(configuration["numberOfThreads"])        # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        if "warningTime" not in configuration:
            raise Exception("WatchDog needs a \"warningTime\" value in init file")      # self.raiseException
        configuration["warningTime"] = int(configuration["warningTime"])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        self.minimumRemainingTime = { "thread" : "", "remainingTime" : configuration["triggerTime"] + configuration["timeout"] }     # to monitor system stability

        # set global watch dog trigger time
        self.set_watchDogMinimumTime(configuration["triggerTime"])

        # register to general watch dog topic since this is the watch dog super class
        self.mqttSubscribeTopic(self.watchDogTopic + "/#")      # if this class is not overwritten then it has the same name as the default watch dog toppic and will register to "<projectName>/WatchDog/#" twice what is not a problem!

        self.logger.info(self, "init (WatchDog)")


    def calculateNextTimeoutTime(self):
        return Supporter.getTimeStamp() + self.configuration["triggerTime"] + self.configuration["timeout"]


    def calculateRemainingTime(self, lastTimeStamp : int):
        return lastTimeStamp - Supporter.getTimeStamp()


    def threadInitMethod(self):
        self.watchDogLastInformedInitTime = self.calculateNextTimeoutTime() + self.configuration["triggerTime"]     # initial timeout after that all threads must have been seen at least once
        self.watchDogLastInformedDict = {}                                                                          # to collect all known threads so far with next timeout time


    def threadMethod(self):
        # give threads a chance to inform the watch dog
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            if "sender" in newMqttMessageDict:
                # ensure there is a timestamp for the sender of the actually received message (if not use startup timeout)
                if newMqttMessageDict["sender"] not in self.watchDogLastInformedDict:
                    self.watchDogLastInformedDict[newMqttMessageDict["sender"]] = self.watchDogLastInformedInitTime

                # calculate remaining time and check if it is shorter as the current minimum remaining time
                timeLeft = self.calculateRemainingTime(self.watchDogLastInformedDict[newMqttMessageDict["sender"]])
                if timeLeft < self.minimumRemainingTime["remainingTime"]:
                    self.minimumRemainingTime["remainingTime"] = timeLeft
                    self.minimumRemainingTime["thread"] = newMqttMessageDict["sender"]

                # finally set new timeout for current sender
                self.watchDogLastInformedDict[newMqttMessageDict["sender"]] = self.calculateNextTimeoutTime()

            self.logger.debug(self, "received message :" +
                              str(newMqttMessageDict) +
                              ", shortest remaining time: " +
                              Supporter.encloseString(str(self.minimumRemainingTime)))
            
            if self.minimumRemainingTime["remainingTime"] <= self.configuration["warningTime"]:
                self.logger.warning(self, "minimum detected remaining time is very short: " + Supporter.encloseString(str(self.minimumRemainingTime)))

        # check amount of threads first
        if self.watchDogLastInformedInitTime < Supporter.getTimeStamp():
            if len(self.watchDogLastInformedDict) != self.configuration["numberOfThreads"]:
                # @todo ggf. besser noch den HW-Watchdog informieren und danach die exception schmeissen
                raise Exception("watch dog expects " +
                                Supporter.encloseString(str(self.configuration["numberOfThreads"])) +
                                " but got " +
                                Supporter.encloseString(str(len(self.watchDogLastInformedDict))) +
                                " within timeout time:\n" + "\n".join(self.watchDogLastInformedDict.keys()))

        # now check all (already stored) timeout times
        for thread in self.watchDogLastInformedDict:
            if self.watchDogLastInformedDict[thread] < Supporter.getTimeStamp():
                # @todo ggf. besser noch den HW-Watchdog informieren und danach die exception schmeissen
                raise Exception("thread " +
                                Supporter.encloseString(thread) +
                                "timed out")

        deltaTime = Supporter.getDeltaTime(self.startupTime)
        self.logger.trace(self, "WatchDog thread up since " + str(deltaTime) + " seconds = " + self.name)

        time.sleep(0.5)

