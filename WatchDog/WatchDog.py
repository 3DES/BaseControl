import time
import json
from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


class WatchDog(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)

        # check and prepare mandatory parameters
        self.tagsIncluded(["triggerTime", "timeout", "warningTime"], intIfy = True) 
        self.tagsIncluded(["expectThreads"])
        if self.tagsIncluded(["ignoreThreads"], optional = True, default = []):     # empty list in that case for easier handling
            self.configuration["expectThreads"].extend(self.configuration["ignoreThreads"])             # add ignoreThreads to expectedThreads now so they don't have to be given in both lists
            self.configuration["ignoreThreads"] = list(set(self.configuration["ignoreThreads"]))        # ensure each thread is contained only once
            self.configuration["expectThreads"] = list(set(self.configuration["expectThreads"]))        # ensure each thread is contained only once

        self.tagsIncluded(["setupTime"], optional = True, default = configuration["triggerTime"])   # if (optional) setupTime is not given use triggerTime instead
        self.tagsIncluded(["logUpTime"], intIfy = True, optional = True, default = 0)

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

        # init lastDeltaTime to be compared with current delta time to show proper up-time message 
        self.lastDeltaTime = Supporter.getSecondsSince(self.startupTime)


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
                    sender = json.loads(newMqttMessageDict["content"])["sender"]

                    # do we expect a thread with this name?
                    if sender not in self.configuration["expectThreads"]:
                        raise Exception("watch dog found unexpected thread [" + sender + "]")
                    
                    # ensure there is a timestamp for the sender of the currently received message (if not use startup timeout)
                    if sender not in self.watchDogLastInformedDict:
                        self.watchDogLastInformedDict[sender] = self.watchDogLastInformedInitTime   # this will immediately be overwritten with current time but we need the startup time here for remaining time calculation

                    # ignore "ingored" threads otherwise timing calculation for diagnosis could get damaged
                    if sender not in self.configuration["ignoreThreads"]:
                        # calculate remaining time and check if it is shorter as the current minimum remaining time
                        timeLeft = self.calculateRemainingTime(self.watchDogLastInformedDict[sender])
                        if timeLeft < self.minimumRemainingTime["remainingTime"]:
                            self.minimumRemainingTime["remainingTime"] = timeLeft
                            self.minimumRemainingTime["thread"] = sender

                        # finally set new timeout for current sender
                        self.watchDogLastInformedDict[sender] = self.calculateNextTimeoutTime()

            # log received message and shortest detected remaining time ever
            self.logger.debug(self, "received message :" +
                              str(newMqttMessageDict) +
                              ", shortest remaining time: " +
                              Supporter.encloseString(str(self.minimumRemainingTime)))

            # warning in case minimum remaining time becomes shorter than defined warning time
            if self.minimumRemainingTime["remainingTime"] <= self.configuration["warningTime"]:
                self.logger.warning(self, "minimum detected remaining time is very short: " + Supporter.encloseString(str(self.minimumRemainingTime)))

        # after setup time is over once check amount of threads each time thread loop is executed
        if Supporter.getTimeStamp() >= self.watchDogLastInformedInitTime:
            # create a union of expected and already found threads and check length what has to be identical!
            if len(self.configuration["expectThreads"]) != len(self.watchDogLastInformedDict):
                missedThreads = []
                for expectedThread in self.configuration["expectThreads"]:
                    if expectedThread not in self.watchDogLastInformedDict:
                        missedThreads.append(expectedThread)
                # @todo ggf. besser noch den HW-Watchdog informieren und danach die exception schmeissen
                raise Exception("watch dog expects [" +
                                str(len(self.configuration["expectThreads"])) +
                                "] but got only " +          # we know we have less since unknown threads are handled somewhere else and not stored in known thread list!
                                Supporter.encloseString(str(len(self.watchDogLastInformedDict))) +
                                " within timeout time (" +
                                str(self.configuration["triggerTime"] + self.configuration["timeout"] + self.configuration["setupTime"]) + 
                                "s), missing:\n" + "\n".join(missedThreads))

        # now check all (already stored) timeout times
        for thread in self.watchDogLastInformedDict:
            if self.watchDogLastInformedDict[thread] < Supporter.getTimeStamp():
                # thread in timeout ignore list, only then suppress exception!
                if not thread in self.configuration["ignoreThreads"]:
                    # @todo ggf. besser noch den HW-Watchdog informieren und danach die exception schmeissen
                    raise Exception("thread " +
                                    Supporter.encloseString(thread) +
                                    "timed out")

        # log system running time (except it has been deactivated by "logUpTime" == 0)
        if self.configuration["logUpTime"]:
            deltaTime = Supporter.getSecondsSince(self.startupTime)
            if self.lastDeltaTime + self.configuration["logUpTime"] <= deltaTime:
                self.logger.info(self, "WatchDog thread up since " + str(deltaTime) + " seconds = " + self.name)
                self.lastDeltaTime = deltaTime


    def threadBreak(self):
        '''
        Set defined thread break time (since common time could have been changed!)
        '''
        time.sleep(0.5)


