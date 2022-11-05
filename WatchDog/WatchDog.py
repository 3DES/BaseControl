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
        self.tagsIncluded(["triggerTime", "timeout", "numberOfThreads", "warningTime"], intIfy = True) 

        # setupTime is identical with triggerTime if it hasn't been given
        if "setupTime" not in configuration:
            configuration["setupTime"] = configuration["triggerTime"]                   # if (optional) setupTime is not given use triggerTime instead

        # prepare optional value
        if not self.tagsIncluded(["upTime"], intIfy = True, optional = True):
            configuration["upTime"] = 0

        # ensure there is a "debug" element even if it wasn't defined in init file and ensure it's 0 except it has been defined as 1
        if not self.tagsIncluded(["debug"], intIfy = True, optional = True) or not (configuration["debug"] == 1):
            configuration["debug"] = 0

        self.minimumRemainingTime = { "thread" : "", "remainingTime" : configuration["triggerTime"] + configuration["timeout"] }     # to monitor system stability remember shortest ever seen remaining trigger time

        # set global watch dog trigger time
        self.set_watchDogMinimumTime(configuration["triggerTime"])

        # register to general watch dog topic since this is the watch dog super class
        self.mqttSubscribeTopic(self.createInTopicFilter(self.watchDogTopic))      # if this class is not overwritten then it has the same name as the default watch dog toppic and will register to "<projectName>/WatchDog/#" twice what is not a problem!

        self.logger.info(self, "init (WatchDog)")


    def calculateNextTimeoutTime(self):
        '''
        Next timeout time is current time + defined trigger time + defined timeout time (this allows the threads to set up a timer for trigger time and have still timeout time available for sending message to watch dog)
        '''
        return Supporter.getTimeStamp() + self.configuration["triggerTime"] + self.configuration["timeout"]


    def calculateRemainingTime(self, lastTimeStamp : int):
        '''
        Remaining time is calculated next time a trigger is requested minus current time
        a negative remaining time means the trigger time has been exceeded what means timeout!
        '''
        return lastTimeStamp - Supporter.getTimeStamp()


    def threadInitMethod(self):
        '''
        Overwritten thread init method
        '''
        self.watchDogLastInformedInitTime = self.calculateNextTimeoutTime() + self.configuration["setupTime"]       # initial timeout after that all threads must have been seen at least once (use "setupTime" here since it could take some more time until all threads have been set up)
        self.watchDogLastInformedDict = {}                                                                          # to collect all known threads so far with next timeout time

        # if "debug" has been set to 1 allow threads to disable monitoring via message
        if self.configuration["debug"]:
            self.disableMonitoring = set()
            
        # init lastDeltaTime to be compared with current delta time to show proper up-time message 
        self.lastDeltaTime = Supporter.getDeltaTime(self.startupTime)


    def threadMethod(self):
        '''
        Overwritten thread main method
        '''
        # give threads a chance to inform the watch dog
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            # handle received message, if newMqttMessageDict["content"]["sender"] is included this thread must be still alive
            if "content" in newMqttMessageDict:
                if "sender" in newMqttMessageDict["content"]:
                    sender = newMqttMessageDict["content"]["sender"]
                    # ensure there is a timestamp for the sender of the currently received message (if not use startup timeout)
                    if sender not in self.watchDogLastInformedDict:
                        self.watchDogLastInformedDict[sender] = self.watchDogLastInformedInitTime   # this will immediately be overwritten with current time but we need the startup time here for remaining time calculation

                    # calculate remaining time and check if it is shorter as the current minimum remaining time
                    timeLeft = self.calculateRemainingTime(self.watchDogLastInformedDict[sender])
                    if timeLeft < self.minimumRemainingTime["remainingTime"]:
                        self.minimumRemainingTime["remainingTime"] = timeLeft
                        self.minimumRemainingTime["thread"] = sender

                    # finally set new timeout for current sender
                    self.watchDogLastInformedDict[sender] = self.calculateNextTimeoutTime()

                    # only if debug == 1 and disable == 1 then disable monitoring for sender thread
                    if self.configuration["debug"] and ("disable" in newMqttMessageDict["content"]) and newMqttMessageDict["content"]["disable"]:
                        self.disableMonitoring.add(newMqttMessageDict["content"]["sender"])
                    else:
                        # in all other cases enable thread (each trigger message without "disable":1 tag removes the thread immediately from ignore list)
                        self.disableMonitoring.discard(newMqttMessageDict["content"]["sender"])

            # log received message and shortest detected remaining time ever
            self.logger.debug(self, "received message :" +
                              str(newMqttMessageDict) +
                              ", shortest remaining time: " +
                              Supporter.encloseString(str(self.minimumRemainingTime)))

            # warning in case minimum remaining time becomes shorter than defined warning time
            if self.minimumRemainingTime["remainingTime"] <= self.configuration["warningTime"]:
                self.logger.warning(self, "minimum detected remaining time is very short: " + Supporter.encloseString(str(self.minimumRemainingTime)))

        # after setup time is over once check amount of threads each time thread loop is executed
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
                # thread must be ignored AND debug must be enabled to suppress exceptions!
                if not (self.configuration["debug"] and thread in self.disableMonitoring):
                    # @todo ggf. besser noch den HW-Watchdog informieren und danach die exception schmeissen
                    raise Exception("thread " +
                                    Supporter.encloseString(thread) +
                                    "timed out")

        # log system running time (except it has been deactivated by "upTime" == 0)
        if self.configuration["upTime"]:
            deltaTime = Supporter.getDeltaTime(self.startupTime)
            if self.lastDeltaTime + self.configuration["upTime"] <= deltaTime:
                self.logger.info(self, "WatchDog thread up since " + str(deltaTime) + " seconds = " + self.name)
                self.lastDeltaTime = deltaTime


    def threadBreak(self):
        '''
        Set defined thread break time (since common time could have been changed!)
        '''
        time.sleep(0.5)


