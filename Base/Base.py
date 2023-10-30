from Base.Supporter import Supporter
import sys


class Base(object):
    '''
    classdocs
    '''


    QUEUE_SIZE = 300            # length of Logger and MqttBridge Queues
    QUEUE_SIZE_EXTRA = 100      # must be at least as large as the maximum number of expected threads and interfaces!
    JOIN_TIME  = 5


    # @todo ggf. _SIMULATE umbenennen zu __SIMULATE!
    # @todo externen WD nicht triggern, wenn ein Objekt im Simulations-Moduls l�uft!
    _SIMULATE = False            # to be set to True as soon as at least one of the objects are simulating values, this will prevent the external watchdog relay from being triggered


    @classmethod
    def setSimulate(cls):
        Base._SIMULATE = True


    @classmethod
    def getSimulate(cls):
        return Base._SIMULATE


    def toSimulate(self):
        '''
        Should current object run in simulation mode?
        '''
        if self.tagsIncluded(["SIMULATE"], optional = True, default = False):
            return self.configuration["SIMULATE"]


    def __init__(self, baseName : str, configuration : dict):
        '''
        Constructor
        '''
        self.name = baseName                                                # set name for this thread
        self.configuration = configuration                                  # remember given configuration
        #super().__init__()        # NO!!!  -->  https://stackoverflow.com/questions/9575409/calling-parent-class-init-with-multiple-inheritance-whats-the-right-way

        # check if current object has parameter "SIMULATE" set to True
        if self.toSimulate():
            self.setSimulate()
            Supporter.debugPrint(f"SIMULATE set")      # @todo Prio1 hierauf muessen wir noch reagieren und dafür sorgen, daß die Anlage nicht einschaltet!!!


    def _getCounterName(self, name : str):
        return f"counter_{self.name}_{name}"


    def _getTimerName(self, name : str):
        return f"timer_{self.name}_{name}"


    def _getOneShotTimer(self, timerName : str):
        '''
        A timer name (created by self._getTimerName()) has to be given and it will be converted into a one shot timer name
        A one-shot timer has to be renamed to <timerName>__oneshot when it shot once, so it will not shoot again
        '''
        return f"{timerName}__oneshot"


    def counterExists(self, name : str):
        '''
        To check if a counter already exists
        '''
        nameSpace = globals()
        return self._getCounterName(name) in nameSpace
        

    def timerExists(self, name : str):
        '''
        To check if a timer already exists
        '''
        nameSpace = globals()
        timerName = self._getTimerName(name)
        return (timerName in nameSpace) or (self._getOneShotTimer(timerName) in nameSpace)


    def counter(self, name : str, value : int = 0, autoReset : bool = True, singularTrue : bool = False, remove : bool = False, getValue : bool = False, dontCount : bool = False, startWithOne : bool = False):
        '''
        Simple counter returns True if counter has called given amount of times whereby the setup call already counts as the first call!
        Each time it's called it counts up

        given value has to be a positive integer, otherwise an exception will be thrown
        if not given default value 0 will be taken, what is not allowed to set a timer up but what is fine if the timer is already set up

        autoReset will reset counter when given amount of calls have been reached
        if autoReset is False a value is not necessary but in that case it will never become True, so it usually only makes sense to get the counter value instead of the boolean result

        singularTrue will return True only when the given value is equal to the counter but not if it is greater than the counter (for this feature autoReset and getValue must be False)

        if remove is True the counter will be removed
        
        if getValue is set to True the counter value will be given back instead of True/False, in that case "value-1" is equivalent to True and depending on singularTrue all values greater than "value-1" are also True
        
        with dontCount set to True the current value can be read without changing the counter value
        
        if startWithOne is True counter counts [1..value], otherwise counter counts [0..value-1], this can only be set during setup, to change it counter has to be removed and set up again
        '''
        counterName = self._getCounterName(name)
        nameSpace = globals()

        if remove:
            if counterName not in nameSpace:
                raise Exception("counter " + name + " cannot be deleted since it doesn't exist")
            del(nameSpace[counterName])
            return True
        else:
            if counterName not in nameSpace:
                if value < 1:
                    if not autoReset:
                        # without autoReset a counter simply counts so no value is necessary
                        value = 1
                    else:
                        # with autoReset a counter is necessary otherwise it's not decidible when counter flows over
                        raise Exception("A counter cannot be set up with any value less than 1 except autoReset has been set to False")
                # create local variable with name given in string (usually we could fill it with one array but by filling it value by value it's clear what element is used for what)
                nameSpace[counterName] = [0, 0, 0]
                nameSpace[counterName][0] = 1               # counter internally always starts with 1
                nameSpace[counterName][1] = value           
                nameSpace[counterName][2] = startWithOne    # only influences the value given back but not the internal counter value
            else:
                if value < 1:
                    value = nameSpace[counterName][1]                   # take stored value instead of given one
                else:
                    nameSpace[counterName][1] = value                   # change timer threshold

                if not dontCount:
                    # stop counting up when value + 1 has been reached (otherwise counter would count up endless)
                    if nameSpace[counterName][0] < value or not autoReset:
                        nameSpace[counterName][0] += 1
                    else:
                        # auto reset value if given
                        nameSpace[counterName][0] = 1       # counter internally always is reset to 1

            if getValue:
                # counter usually starts by one but it's possible to set "startWithOne = False" to get a counter start counting by zero, therefore decrease coutner value by one in that case  
                return nameSpace[counterName][0] if nameSpace[counterName][2] else (nameSpace[counterName][0] - 1) 
            else:
                # return True if "counter == value" or in case "counter > value" only if singularTrue has not been given, otherwise return False
                return (nameSpace[counterName][0] == value) or (nameSpace[counterName][0] > value and not singularTrue) 


    def timer(self, name : str, timeout : int = 0, startTime : int = 0, remove : bool = False, removeOnTimeout : bool = False, strict : bool = False, setup : bool = False, remainingTime : bool = False, oneShot : bool = False, firstTimeTrue : bool = False, autoReset : bool = True):
        '''
        Simple timer returns True if given timeout has been reached or exceeded

        A timeout value of 0 will not setup a not existing timer but can be used to check a running timer and reset it if it exceeded, the original period will not be changed
        A timeout different from 0 will setup a new timer if it doesn't exist or set a new time period if timeout is different but the current set time will not be changed

        The timer can jitter (depending on your read timing) but it will never drift away!

        If startTime is not given current time will be taken, if startTiem has been given it will only be taken to setup the timer but will be ignored if the timer is already running, so a timer can be set up and checked with the same line of code

        If remove is True the timer will be deleted
        If removeOnTimeout is True and the timer has timed out already it will be deleted, but the current result will be returned

        If strict is True an Exception will be thrown in case more than one timeout period has passed over since last call, so calling is too slow and timeout events have been lost

        If setup is True timer will be set up even if it already exists, but remove has higher priority if also given, in that case no new timer will be set up!

        If remainingTime is True timer handling is as usual but the remaining time will be given back instead of True or False, check can be done by comparing the returned value with 0, a positive value (= False) means there is still some time left, a negative value (= True) means time is already over 

        During setup call the timer usually returns with False but if firstTimeTrue is set to True it will return with True for the first time, so it's not necessary to handle it manually to get informed at setup call, too and not only for all following periods

        In case of oneShot is set to True the timer will only return True once when the time is over, it returns True independent from how long the time is already over but only for the first check after the timeout has been reached
        oneShot has no effect if given when the timer is set up but it has to be given when the timer is checked

        autoReset = False prevents timer from being reset when it has timed out, so a once timed out timer will stay timed out; therefore, it's similar to oneShot but if it becomes True it stays True whereas oneShot is True exactly once
        autoReset = True ensures that the time between timer events stays always the same, so you will see a jitter since it depends when you call the timer but you will never see a drift, missed periods are gone but the next one will also be synchronized again!
        '''
        def updateTime(startTime : int, period : int):
            '''
            Internal method to do the timer math
            '''
            currentTime = Supporter.getTimeStamp()
            if currentTime < startTime:
                # start time not yet reached!
                return startTime
            else:
                # 1) currentTime == startTime
                #    --> ensure next event will happen in period seconds
                # 2) currentTime > startTime
                #    --> ensure next event will happen synchronized to next possible "startTime + n * period" seconds
                deltaTime = currentTime - startTime
                return startTime + period * ((deltaTime // period) + 1)

        NEXT_TIMEOUT_TIME = 0
        PERIOD_DURATION = 1
        ONE_SHOT_DONE = -1

        setupTurn = False
        timerName        = self._getTimerName(name)
        oneShotTimerName = self._getOneShotTimer(timerName)
        nameSpace = globals()
        if (timerName in nameSpace) or (oneShotTimerName in nameSpace):
            timerAlreadySetUp = True
            if timerName in nameSpace:
                existingTimerName = timerName
            else:
                existingTimerName = oneShotTimerName
        else:
            timerAlreadySetUp = False

        if remove:
            if not timerAlreadySetUp:
                raise Exception("timer " + timerName + " cannot be deleted since it doesn't exist")
            del(globals()[existingTimerName])
            return True
        else:
            # setup timer in global namespace if necessary
            if timeout > 0:
                if (not timerAlreadySetUp) or setup:
                    if startTime == 0:
                        startTime = Supporter.getTimeStamp()                            # startTime is needed, if it hasn't been given take current time instead
                    # timer doesn't exist so use "timerName" because "existingTimerName" is None
                    nameSpace[timerName] = [updateTime(startTime, timeout), timeout]    # create local variable with name given in string
                    setupTurn = True                                                    # timer has been setup in this call
                    existingTimerName = timerName
                else:
                    nameSpace[existingTimerName][PERIOD_DURATION] = timeout             # update timer period for following interval but not for the currently running one
            elif not timerAlreadySetUp:            # timeout is 0 otherwise we wouldn't be here!
                raise Exception("a timer cannot be set up with a timeout of 0")

            currentTime = Supporter.getTimeStamp()
            if currentTime >= nameSpace[existingTimerName][NEXT_TIMEOUT_TIME]:          # timeout happened?
                if existingTimerName == timerName:                                      # common timer or one-shot-timer that is still active
                    originalTimeout = nameSpace[existingTimerName][NEXT_TIMEOUT_TIME]
                    
                    if strict:
                        deltaTime = currentTime - originalTimeout 
                        fullPeriodes = int(deltaTime / nameSpace[existingTimerName][PERIOD_DURATION]) 
                        if fullPeriodes > 1:    # delta must be less than 2 periods otherwise throw exception
                            raise Exception("Timer has been polled too slowly so more than one timeout period passed over and some events have been missed, event happened occurred " + str(deltaTime) + " seconds ago")

                    if oneShot:
                        if nameSpace[existingTimerName][NEXT_TIMEOUT_TIME] != ONE_SHOT_DONE:
                            # oneShot timer shoot only once so remember that is has shot already!
                            nameSpace[existingTimerName][NEXT_TIMEOUT_TIME] = ONE_SHOT_DONE

                            # timeout happened, so remove timer if "removeOnTimeout" has been given
                            if removeOnTimeout:
                                del(globals()[existingTimerName])

                            return True
                        else:
                            # shot already, will not shoot again
                            return False
                    elif autoReset:
                        # the "if/elif" ensures that oneShot implicitly means autoReset=False, but on the other hand independently from oneShot autoReset can be set to False if needed
                        nameSpace[existingTimerName][NEXT_TIMEOUT_TIME] = updateTime(nameSpace[existingTimerName][NEXT_TIMEOUT_TIME], nameSpace[existingTimerName][PERIOD_DURATION])

                    # timeout happened, so remove timer if "removeOnTimeout" has been given
                    if removeOnTimeout:
                        del(globals()[existingTimerName])

                    if remainingTime:
                        return originalTimeout - currentTime
                    else:
                        return True
                else:
                    # timeout happened, so remove timer if "removeOnTimeout" has been given
                    if removeOnTimeout:
                        del(globals()[existingTimerName])

                    if remainingTime:
                        return originalTimeout - currentTime
                    else:
                        return False            # one-shot-timer shot already so don't shoot again
            else:
                if remainingTime:
                    return nameSpace[existingTimerName][NEXT_TIMEOUT_TIME] - currentTime
                else: 
                    return False or (setupTurn and firstTimeTrue)



