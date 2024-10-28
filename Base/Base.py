from Base.Supporter import Supporter
import Logger.Logger
from Base.ExtendedJsonParser import ExtendedJsonParser


class Base():
    '''
    classdocs
    '''
    QUEUE_SIZE = 300            # length of Logger and MqttBridge Queues
    QUEUE_SIZE_EXTRA = 100      # must be at least as large as the maximum number of expected threads and interfaces!
    JOIN_TIME  = 5

    # @todo ggf. _SIMULATE umbenennen zu __SIMULATE!
    # @todo externen WD nicht triggern, wenn ein Objekt im Simulations-Modus laeuft!
    _SIMULATE = False            # to be set to True as soon as at least one of the objects are simulating values, this will prevent the external watchdog relay from being triggered
    _SIMULATION_ALLOWED = False  

    @classmethod
    def setSimulationModeAllowed(cls, simulationAllowed : bool):
        '''
        To be set when command line parameter switches simulation mode on
        '''
        Base._SIMULATION_ALLOWED = Base._SIMULATION_ALLOWED or simulationAllowed        # never set back to False if ever was True!


    @classmethod
    def setGlobalSimulationMode(cls):
        '''
        To be set when at least one thread or interface runs in simulation mode!
        '''
        Base._SIMULATE = True
        if Base._SIMULATE and not Base._SIMULATION_ALLOWED:
            Logger.Logger.Logger.get_logger().warning(Supporter.getCaller(), f"SIMULATION flag found in configuration but SIMULATION was not enabled, no SIMULATION at all, is that what you want?")


    @classmethod
    def getGlobalSimulationMode(cls):
        '''
        To check if at least one thread or interface runs in simulation mode
        '''
        return Base._SIMULATE


    def tagsIncluded(self, tagNames : list, intIfy : bool = False, optional : bool = False, configuration : dict = None, default = None) -> bool:
        '''
        Checks if given parameters are contained in task configuration
        
        A dictionary with configuration can be given optionally for the case that configuration has to be checked before super().__init__() has been called
        if intIfy is True it will be ensured that the value contains an integer
        if optional is True no exception will be thrown if element is missed, in that case the return value will be True if all given tags have been included or False if at least one wansn't included
        '''
        success = True

        # take given configuration or self.configuration, if none is available throw an exception
        if configuration is None:
            if not hasattr(self, "configuration"):
                raise Exception("tagsIncluded called without a configuration dictionary and without self.configuration set")
            configuration = self.configuration

        # check and prepare mandatory parameters
        for tagName in tagNames:
            if tagName not in configuration:
                # in case of not optional throw an exception
                if not optional:
                    raise Exception(self.name + " needs a \"" + tagName + "\" value in init file")

                # if there was only one element to check and it doesn't exist, set default value
                if len(tagNames) == 1:
                    configuration[tagName] = default
                success = False         # remember there was at least one missing element
            elif intIfy:
                configuration[tagName] = int(configuration[tagName])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)

        return success


    def toSimulate(self):
        '''
        Should current object run in simulation mode?
        '''
        if self.tagsIncluded(["SIMULATE"], optional = True, default = False):
            return self.configuration["SIMULATE"]
        return None


    def __init__(self, baseName : str, configuration : dict):
        '''
        Constructor
        '''
        self.name = baseName                                                # set name for this thread
        self.configuration = configuration                                  # remember given configuration
        #super().__init__()        # NO!!!  -->  https://stackoverflow.com/questions/9575409/calling-parent-class-init-with-multiple-inheritance-whats-the-right-way

        # check if current object has parameter "SIMULATE" set to True
        if self.toSimulate():
            self.setGlobalSimulationMode()
            Supporter.debugPrint(f"SIMULATE set")      # @todo Prio1 hierauf muessen wir noch reagieren und dafür sorgen, daß die Anlage nicht einschaltet!!!

        # add dicts for counters, timers and accumulators to namespace
        self.COUNTER_DICT     = f"__counter_{self.name}"
        self.TIMER_DICT       = f"__timer_{self.name}"
        self.ACCUMULATOR_DICT = f"__accumulator_{self.name}"
        nameSpace = globals()
        nameSpace[self.COUNTER_DICT]     = {}
        nameSpace[self.TIMER_DICT]       = {}
        nameSpace[self.ACCUMULATOR_DICT] = {}
        self.extendedJson = ExtendedJsonParser()       #  every child needs its own extended json parser otherwise we have a race condition!


    def _createCounter(self, name : str, content : dict):
        nameSpace = globals()
        nameSpace[self.COUNTER_DICT][name] = content

    def _getCounter(self, name):
        if self.counterExists(name):
            nameSpace = globals()
            return nameSpace[self.COUNTER_DICT][name]
        return None

    def _removeCounter(self, name : str):
        if self.counterExists(name):
            nameSpace = globals()
            nameSpace[self.COUNTER_DICT][name] = None
        else:
            raise Exception(f"cannot remove counter {name} since it doesn't exist or has been removed already")

    def _createTimer(self, name : str, content : dict):
        nameSpace = globals()
        nameSpace[self.TIMER_DICT][name] = content

    def _getTimer(self, name):
        if self.timerExists(name):
            nameSpace = globals()
            return nameSpace[self.TIMER_DICT][name]
        return None

    # @todo was ist mit diesen Funktionen hier, aktuell nimmt die keiner her, koennen die weg oder sollten wir die verwenden?!?!?
    def _removeTimer(self, name : str):
        if self.timerExists(name):
            nameSpace = globals()
            nameSpace[self.TIMER_DICT][name] = None
        else:
            raise Exception(f"cannot remove timer {name} since it doesn't exist or has been removed already")

    def _createAccumulator(self, name : str, content : dict):
        nameSpace = globals()
        nameSpace[self.ACCUMULATOR_DICT][name] = content

    def _getAccumulator(self, name):
        if self.accumulatorExists(name):
            nameSpace = globals()
            return nameSpace[self.ACCUMULATOR_DICT][name]
        return None

    def _removeAccumulator(self, name : str):
        if self.accumulatorExists(name):
            nameSpace = globals()
            nameSpace[self.ACCUMULATOR_DICT][name] = None
        else:
            raise Exception(f"cannot remove accumulator {name} since it doesn't exist or has been removed already")


    def counterExistedButRemoved(self, name :  str) -> str:
        '''
        Checks if counter name ever existed but has been removed again
        
        @param name   name of the counter to be checked
        @return       True if counter ever existed but has been removed again, False if counter hasn't ever existed
        '''
        nameSpace = globals()
        return (name is not None) and (name in nameSpace[self.COUNTER_DICT]) and (nameSpace[self.COUNTER_DICT][name] is None)


    def counterExists(self, name : str):
        '''
        To check if a counter already exists
        
        @param name    counter to be checked
        @return        name if counter exists, None if not
        '''
        nameSpace = globals()
        if (name is None) or (name not in nameSpace[self.COUNTER_DICT]) or ((name in nameSpace[self.COUNTER_DICT]) and (nameSpace[self.COUNTER_DICT][name] is None)):
            name = None
        return name


    def timerExistedButRemoved(self, name :  str) -> str:
        '''
        Checks if timer name ever existed but has been removed again
        
        @param name     name of the timer to be checked
        @return         True if timer ever existed but has been removed again, False if timer hasn't ever existed
        '''
        nameSpace = globals()
        return (name is not None) and (name in nameSpace[self.TIMER_DICT]) and (nameSpace[self.TIMER_DICT][name] is None)


    def timerExists(self, name : str) -> str:
        '''
        To check if a timer already exists
        
        @param name    timer to be checked
        @return        name if timer exists, None if not
        '''
        nameSpace = globals()
        if (name is None) or (name not in nameSpace[self.TIMER_DICT]) or ((name in nameSpace[self.TIMER_DICT]) and (nameSpace[self.TIMER_DICT][name] is None)):
            name = None
        return name


    def accumulatorExistedButRemoved(self, name :  str) -> str:
        '''
        Checks if accumulator name ever existed but has been removed again
        
        @param name   name of the accumulator to be checked
        @return       True if accumulator ever existed but has been removed again, False if accumulator hasn't ever existed
        '''
        nameSpace = globals()
        return (name is not None) and (name in nameSpace[self.ACCUMULATOR_DICT]) and (nameSpace[self.ACCUMULATOR_DICT][name] is None)


    def accumulatorExists(self, name : str):
        '''
        To check if an accumulator already exists
        '''
        nameSpace = globals()
        if (name is None) or (name not in nameSpace[self.ACCUMULATOR_DICT]) or ((name in nameSpace[self.ACCUMULATOR_DICT]) and (nameSpace[self.ACCUMULATOR_DICT][name] is None)):
            name = None
        return name


    def counterRemove(self, counterName : str, exception : bool = True) -> bool:
        '''
        Checks if a counter exists and removes it in that case, but it isn't really removed but instead counter dict will be set to None, so it can be checked if a not existing counter or an already removed counter is removed
        Whereas removing an already removed counter is OK removing a not existing counter is always a bug!
        
        @param counterName     name of the counter
        @param exception       if a never existed counterName has been given an exception will be thrown since that is usually a bug, but by setting this value to False the exception can be suppressed and None will be returned instead
        @return                True if counter exists, False if counter existed but has already been deleted, None if counter never existed but throwing an exception has been suppressed
                               Exception in case counterName is None or counter never existed, and throwing exceptions hasn't been suppressed, because that must be a development bug!
        '''
        if self.counterExists(counterName):
            self._removeCounter(counterName)
            return True
        elif self.counterExistedButRemoved(counterName):
            return False
        elif exception:
            # counter never existed so that must be a development error!
            raise Exception("counter " + counterName + " cannot be deleted since it doesn't exist")
        return None


    def timerRemove(self, timerName : str, exception : bool = True) -> bool:
        '''
        Checks if a timer exists and removes it in that case, but it isn't really removed but instead timer list will be set to None, so it can be checked if a not existing timer or an already removed timer is removed
        Whereas removing an already removed timer is OK removing a not existing timer is always a bug!
        
        @param timerName       name of the timer
        @param exception       if a never existed timerName has been given an exception will be thrown since that is usually a bug, but by setting this value to False the exception can be suppressed and None will be returned instead
        @return                True if timer exists, False if timer existed but has already been deleted, None if timer never existed but throwing an exception has been suppressed
                               Exception in case timerName is None or timer never existed, and throwing exceptions hasn't been suppressed, because that must be a development bug!
        '''
        if self.timerExists(timerName):
            nameSpace = globals()
            nameSpace[self.TIMER_DICT][timerName] = None
            return True
        elif self.timerExistedButRemoved(timerName):
            return False
        elif exception:
            # timer never existed so that must be a development error!
            raise Exception("timer " + timerName + " cannot be deleted since it doesn't exist")
        return None


    def accumulatorRemove(self, accumulatorName : str, exception : bool = True) -> bool:
        '''
        Checks if a accumulator exists and removes it in that case, but it isn't really removed but instead accumulator list will be set to None, so it can be checked if a not existing accumulator or an already removed accumulator is removed
        Whereas removing an already removed accumulator is OK removing a not existing accumulator is always a bug!
        
        @param accumulatorName name of the accumulator
        @param exception       if a never existed accumulatorName has been given an exception will be thrown since that is usually a bug, but by setting this value to False the exception can be suppressed and None will be returned instead
        @return                True if accumulator exists, False if accumulator existed but has already been deleted, None if accumulator never existed but throwing an exception has been suppressed
                               Exception in case accumulatorName is None or accumulator never existed, and throwing exceptions hasn't been suppressed, because that must be a development bug!
        '''
        if self.accumulatorExists(accumulatorName):
            nameSpace = globals()
            nameSpace[self.ACCUMULATOR_DICT][accumulatorName] = None
            return True
        elif self.accumulatorExistedButRemoved(accumulatorName):
            return False
        elif exception:
            # accumulator never existed so that must be a development error!
            raise Exception("accumulator " + accumulatorName + " cannot be deleted since it doesn't exist")
        return None


    def counter(self, name : str, value : int = 0, autoReset : bool = True, singularTrue : bool = False, remove : bool = False, getValue : bool = False, dontCount : bool = False, startWithOne : bool = False):
        '''
        Simple counter returns True if counter has called given amount of times whereby the setup call already counts as the first call!
        Each time it's called it counts up

        given value has to be a positive integer, otherwise an exception will be thrown
        if not given default value 0 will be taken, what is not allowed to set a counter up but what is fine if the counter is already set up

        autoReset will reset counter when given amount of calls have been reached
        if autoReset is False a value is not necessary but in that case it will never become True, so it usually only makes sense to get the counter value instead of the boolean result

        singularTrue will return True only when the given value is equal to the counter but not if it is greater than the counter (for this feature autoReset and getValue must be False)

        if remove is True the counter will be removed
        
        if getValue is set to True the counter value will be given back instead of True/False, in that case "value-1" is equivalent to True and depending on singularTrue all values greater than "value-1" are also True
        
        with dontCount set to True the current value can be read without changing the counter value
        
        if startWithOne is True counter counts [1..value], otherwise counter counts [0..value-1], this can only be set during setup, to change it counter has to be removed and set up again
        '''
        COUNTER_VALUE            = "value"           # key to the current counter value
        COUNTER_THRESHOLD        = "threshold"       # key to the counter threshold value
        COUNTER_STARTS_WITH_ONE  = "startWithOne"    # key to information if counter starts counting with 0 or 1
        COUNTER_RESET_VALUE      = 1                 # internal counter value starts always with 1

        if remove:
            if not self.counterExists(name):
                raise Exception("counter " + name + " cannot be deleted since it doesn't exist")
            self.counterRemove(name)
            return True
        else:
            if not self.counterExists(name):
                if value < 1:
                    if not autoReset:
                        # without autoReset a counter simply counts so no value is necessary
                        value = 1
                    else:
                        # with autoReset a counter is necessary otherwise it's not decidible when counter flows over
                        raise Exception("A counter cannot be set up with any value less than 1 except autoReset has been set to False")
                # create local variable with name given in string (usually we could fill it with one array but by filling it value by value it's clear what element is used for what)
                self._createCounter(name, {
                    COUNTER_VALUE           : COUNTER_RESET_VALUE,  # counter internally always starts with 1
                    COUNTER_THRESHOLD       : value,                # threshold value of the counter
                    COUNTER_STARTS_WITH_ONE : startWithOne          # if True the returned counter value is ["value"] otherwise it's ["value"] - 1 because then the counter starts with 0
                })
            else:
                if value < 1:
                    value = self._getCounter(name)[COUNTER_THRESHOLD]   # take stored value instead of given one
                else:
                    self._getCounter(name)[COUNTER_THRESHOLD] = value   # change counter threshold

                if not dontCount:
                    # stop counting up when value + 1 has been reached (otherwise counter would count up endless)
                    if self._getCounter(name)[COUNTER_VALUE] < value or not autoReset:
                        self._getCounter(name)[COUNTER_VALUE] += 1
                    else:
                        # auto reset value if given
                        self._getCounter(name)[COUNTER_VALUE] = COUNTER_RESET_VALUE       # counter internally always is reset to 1

            if getValue:
                # counter usually starts by one but it's possible to set "startWithOne = False" to get a counter start counting by zero, therefore decrease counter value by one in that case  
                return self._getCounter(name)[COUNTER_VALUE] if self._getCounter(name)[COUNTER_STARTS_WITH_ONE] else (self._getCounter(name)[COUNTER_VALUE] - 1) 
            else:
                # return True if "counter == value" or in case "counter > value" only if singularTrue has not been given, otherwise return False
                return (self._getCounter(name)[COUNTER_VALUE] == value) or (self._getCounter(name)[COUNTER_VALUE] > value and not singularTrue) 


    def timer(self, name : str, timeout : int = 0, startTime : int = 0, minimumStartTime : bool = False, remove : bool = False, removeOnTimeout : bool = False, strict : bool = False, reSetup : bool = False, remainingTime : bool = False, oneShot : bool = False, firstTimeTrue : bool = False, autoReset : bool = True):
        '''
        Simple timer returns True if given timeout has been reached or exceeded

        A timeout value of 0 will not setup a not existing timer but can be used to check a running timer and reset it if it exceeded, the original period will not be changed
        A timeout different from 0 will setup a new timer if it doesn't exist or set a new time period if timeout is different but the current set time will not be changed

        The timer can jitter (depending on your read timing) but it will never drift away!

        If startTime is not given current time will be taken, if startTime has been given it will only be taken to setup the timer but will be ignored if the timer is already running, so a timer can be set up and checked with the same line of code
        if startTime is older than current time current time will be used and next timeout will be calculated, otherwise if startTime is in the future then startTime will the first timeout point in time
        If minimumStartTime has been given it ensures that the period from timer setup time to timeout is at least timeout time long, if startTime or next timeout time is shorter than timeout then timeout will be calculated to next timeout value + another one, e.g. if timeout is 5 minutes, current time is 8:00 o'clock and startTime is 8:03 o'clock then next timeout usually will be at 8:03 o'clock but that is less than 5 minutes, so next timeout time will be at 8:03 o'clock + 5 minutes what is 8:08 o'clock

        If remove is True the timer will be deleted
        If removeOnTimeout is True and the timer has timed out already it will be deleted, but the current result will be returned

        If strict is True an Exception will be thrown in case more than one timeout period has passed over since last call, so calling is too slow and timeout events have been lost

        If reSetup is True timer will be set up independent if it already exists or not, but will be ignored if remove has been given, too, in that case no new timer will be set up!

        If remainingTime is True timer handling is as usual but the remaining time will be given back instead of True or False, check can be done by comparing the returned value with 0, a positive value (= False) means there is still some time left, a negative value (= True) means time is already over 

        During setup call the timer usually returns with False but if firstTimeTrue is set to True it will return with True for the first time, so it's not necessary to handle it manually to get informed at setup call, too and not only for all following periods

        In case of oneShot is set to True the timer will only return True once when the time is over, it returns True independent from how long the time is already over but only for the first check after the timeout has been reached
        oneShot can be given at any time but a timer that became a oneshot once will never become a common timer again what means a oneshot timer cannot be "un-oneshot-ted", therefore, oneshot e.g. can be given when timer is set up but is not necessarily needed when timer is checked or vice-versa

        autoReset = False prevents timer from being reset when it has timed out, so a once timed out timer will stay timed out; therefore, it's similar to oneShot but if it becomes True it stays True whereas oneShot is True exactly once
        autoReset = True ensures that the time between timer events stays always the same, so you will see a jitter since it depends when you call the timer but you will never see a drift, missed periods are gone but the next one will also be synchronized again!
        '''
        def updateTime(startTime : int, period : int, currentTime : int = None, minimumStartTime : bool = False):
            '''
            Internal method to do the timer math
            
            @param startTime            start time to be used
            @param period               period duration to calculate next timeout time
            @param currentTime          if start time is current time and current time is calculated inside this method startTime + period always will be less than currentTime + period what will cause a timeout time of currentTime + 2 * period if minimumStartTime is True but that is not what we want!
            @param minimumStartTime     if True next timeout will be >= currentTime + period
            @return                     next timeout time
            '''
            nextTimeout = 0
            if currentTime is None:
                currentTime = Supporter.getTimeStamp()
            if currentTime < startTime:
                # start time not yet reached!
                nextTimeout = startTime
            else:
                # 1) currentTime == startTime
                #    --> ensure next event will happen in period seconds
                # 2) currentTime > startTime
                #    --> ensure next event will happen synchronized to next possible "startTime + n * period" seconds
                deltaTime = currentTime - startTime
                nextTimeout = startTime + period * ((deltaTime // period) + 1)

            # if minimumStartTime has been given ensures there is a minimum of period time until timeout happens, but still synchronized to startTime
            if minimumStartTime and (nextTimeout < currentTime + period):
                nextTimeout += period
            
            return nextTimeout

        NEXT_TIMEOUT    = "nextTimeout"     # key to store the next timeout time
        PERIOD_DURATION = "period"          # key to store the period duration
        ONE_SHOT_TIMER  = "oneshot"         # key to store if timer is a one-shot timer
        ONE_SHOT_DONE   = -1                # NEXT_TIMEOUT will be set to that value to remember that one-shot timer already shot once

        setupTurn = False
        existingTimerName = self.timerExists(name)

        if remove:
            self.timerRemove(existingTimerName)     # remove timer, even if it has been removed already, but throw exception if timer never existed
            return True
        else:
            currentTime = Supporter.getTimeStamp()

            # setup timer if necessary
            if timeout > 0:
                if (existingTimerName is None) or reSetup:
                    if startTime == 0:
                        startTime = currentTime                                                         # startTime is needed, if it hasn't been given take current time instead
                    # timer doesn't exist or setup has been given so use "timerName" because "existingTimerName" could be None
                    self._createTimer(name, {
                        NEXT_TIMEOUT    : updateTime(startTime, timeout, currentTime, minimumStartTime),
                        PERIOD_DURATION : timeout,
                        ONE_SHOT_TIMER  : oneShot 
                    })     # create local variable with name given in string
                    setupTurn = True                                                                    # timer has been setup in this call
                    existingTimerName = name
                else:
                    self._getTimer(existingTimerName)[PERIOD_DURATION] = timeout                             # update timer period for following interval but not for the currently running one
            elif existingTimerName is None:            # timeout is 0 otherwise we wouldn't be here!
                raise Exception("a timer cannot be set up with a timeout of 0")

            # timeout happened?
            if currentTime >= self._getTimer(existingTimerName)[NEXT_TIMEOUT]:
                if strict:
                    deltaTime = currentTime - self._getTimer(existingTimerName)[NEXT_TIMEOUT]
                    fullPeriodes = int(deltaTime / self._getTimer(existingTimerName)[PERIOD_DURATION]) 
                    if fullPeriodes > 1:    # delta must be less than 2 periods otherwise throw exception
                        raise Exception("Timer has been polled too slowly so more than one timeout period passed over and some events have been missed, event happened occurred " + str(deltaTime) + " seconds ago")

                if oneShot or self._getTimer(existingTimerName)[ONE_SHOT_TIMER]:
                    if self._getTimer(existingTimerName)[NEXT_TIMEOUT] != ONE_SHOT_DONE:
                        # timeout happened, so remove timer if "removeOnTimeout" has been given
                        if removeOnTimeout:
                            self.timerRemove(existingTimerName)
                        else:
                            self._getTimer(existingTimerName)[NEXT_TIMEOUT] = ONE_SHOT_DONE      # one-shot timers shoot only once so remember that is has shot already, since it hasn't been removed!
                            self._getTimer(existingTimerName)[ONE_SHOT_TIMER] = oneShot          # it's possible that timer hasn't been setup as one-shot timer but during check oneShot has been given

                        return True
                    else:
                        # shot already, will not shoot again
                        return False
                elif autoReset:
                    # the "if/elif" ensures that oneShot implicitly means autoReset=False, but on the other hand independently from oneShot autoReset can be set to False if needed
                    self._getTimer(existingTimerName)[NEXT_TIMEOUT] = updateTime(self._getTimer(existingTimerName)[NEXT_TIMEOUT], self._getTimer(existingTimerName)[PERIOD_DURATION])

                # timeout happened, so remove timer if "removeOnTimeout" has been given
                originalTimeout = self._getTimer(existingTimerName)[NEXT_TIMEOUT]
                if removeOnTimeout:
                    self.timerRemove(existingTimerName)

                if remainingTime:
                    return originalTimeout - currentTime
                else:
                    return True
            else:
                if remainingTime:
                    return self._getTimer(existingTimerName)[NEXT_TIMEOUT] - currentTime
                else: 
                    return False or (setupTurn and firstTimeTrue)


    def accumulator(self, name : str, power : float = None, timeout : float = None, synchronized : bool = True, useCounter : bool = False, multiplyTime : bool = False, absolute : bool = True, reSetup : bool = False, autoReset : bool = False, minMaxAverage : bool = False) -> float:
        '''
        To create and handle a power accumulator that gets power values (or any other kind of values that have to be accumulated) and adds them optionally multiplied by their duration times
        If the accumulator is set up for absolute calculation an initial power value can be given if the initial reference value is not 0

        @param name                  name of the power accumulator that will be created in current name space
                                     a list can be given then all accumulators will be handled
        @param power                 power value that has to be accumulated
                                     during setup call if absolute is True the value will be used as reference power value
                                     during setup call if absolute is False and multiplyTime is False the value will be add to calculated value
                                     in all other cases it will just be ignored
        @param timeout               time out value can be given, accumulator will return None until timeout happened, in that case the accumulator will be reset and the last calculated value is given back
                                     this value is only handled during setup but ignored in all following calls
                                     a dictionary can be given to give what is usually used to set timeouts in case name is a list and not just a single string
        @param synchronized          ignored if no timeout has been given, otherwise it tries to synchronize the timeout timer to given timeout period absolute to current day,
                                     i.e. if it is 8:03 now and timeout is 15 minutes then the next timeout will occur at 8:15
                                     in case of useCounter is True this value is ignored
        @param useCounter            use a counter instead of a timer so calls will be counted and timeout will be used as counter threshold value
                                     this value is only used during setup, otherwise it's ignored
        @param multiplyTime          if this is False during setup just the given values will be accumulated
        @param absolute              power values are absolute ones so the power value of the current cycle has to be calculated by subtracting previous power value,
                                     it's not possible to switch the accumulator type while it's counting, only if it doesn't exist or reSetup has been set to True the type is considered
                                     if a power value has been given that is less than the previous one in absolute = True mode an exception will be thrown.
        @param autoReset             ignored if absolute is False, otherwise if absolute is True and autoReset is True
                                     the reference power value will be set to 0 and the given power value will be accumulated
        @param minMaxAverage         find minimum, maximum and average of all given values (up to timeout if given)
        @return                      returns the amount of calculated energy so far, to read energy value only the given power should be 0
                                     except if getTime is True, then the time since accumulator has been set up or since last timeout is returned

        '''
        def calculatePower(accumulatorName : str, power : float, timeStamp : float = None) -> dict:
            accumulatorDict = self._getAccumulator(accumulatorName)
            additionalPower = (power - accumulatorDict["referencePower"])

            # multiply new value by time cycle if activated
            if accumulatorDict["multiplyTime"]:
                additionalPower *= (timeStamp - accumulatorDict["referenceTime"])
                accumulatorDict["referenceTime"] = timeStamp

            # in case of absolute the given power is the new reference power but will not be added to "calculatedEnergy"
            if accumulatorDict["absolute"]:
                accumulatorDict["referencePower"] = power

            # finally add power to calculated energy
            accumulatorDict["calculatedEnergy"] += additionalPower

            # collect values to get minimum, maximum and to calculate average value if needed
            if accumulatorDict["valueCounter"] is not None:
                accumulatorDict["valueCounter"] += 1
                if accumulatorDict["minimum"] is None or accumulatorDict["minimum"] > power:
                    accumulatorDict["minimum"] = power
                if accumulatorDict["maximum"] is None or accumulatorDict["maximum"] < power:
                    accumulatorDict["maximum"] = power
                if accumulatorDict["overallSum"] is None:
                    accumulatorDict["overallSum"] = 0                    
                accumulatorDict["overallSum"] += additionalPower

            return accumulatorDict["calculatedEnergy"]


        def handleAccumulator(name : str, power : float = None, timeout : float = None, currentTime : float = None, synchronized : bool = True, useCounter : bool = False, multiplyTime : bool = False, absolute : bool = True, reSetup : bool = False, autoReset : bool = False, minMaxAverage : bool = False) -> float:
            if type(name) != str:
                raise Exception(f"accumulator must be handled one by one here!")

            # create and check some initial values
            returnValue = None
            resetMinMaxValues = False

            if not self.accumulatorExists(name):
                # setup new timer
                if timeout:
                    # in case of timeout has been given we need a periodic timer
                    timerName = "__created_by_accumulator_" + name
                    if useCounter:
                        if timeout != int(timeout):
                            raise Exception(f"if a counter should be used the timeout parameter must contain an integer, not a float value!")
                        self.counter(timerName, value = timeout)
                    else:
                        self.timer(timerName, timeout, startTime = currentTime if not synchronized else Supporter.getTimeOfToday())
                else:
                    # no timeout, no timer
                    timerName = None

                # create new accumulator
                self._createAccumulator(name, {
                    "referencePower"   : 0,
                    "referenceTime"    : currentTime if multiplyTime else None,         # only needed if used for calculation
                    "timeout"          : timeout,                                       # can be None in case no timeout has been given
                    "timerName"        : timerName,                                     # can be None in case no timeout has been given
                    "calls"            : useCounter,                                    # use a counter instead of a timer
                    "absolute"         : absolute,
                    "autoReset"        : autoReset and absolute,                        # autoReset only works in absolute case, if absolute is False then ignore autoReset
                    "multiplyTime"     : multiplyTime,
                    "valueCounter"     : 0 if minMaxAverage else None,
                    "minimum"          : None,
                    "maximum"          : None,
                    "overallSum"       : None,
                    "calculatedEnergy" : 0
                })
                accumulatorDict = self._getAccumulator(name) 
                if power:
                    if accumulatorDict["absolute"]:
                        # in case of absolute the given power is the new reference power but will not be added to "calculatedEnergy"
                        accumulatorDict["referencePower"] = power
                    elif not accumulatorDict["multiplyTime"]:
                        # not multiplyTime is important here since it's unknown here what time delta should be used to be calculated with power value
                        calculatePower(accumulatorName = name, power = power, timeStamp = currentTime)

                if not accumulatorDict["timerName"]:
                    # calculated energy has to be returned except timer has been configured
                    returnValue = accumulatorDict["calculatedEnergy"]
                #else:
                #    returnValue = None      # return None in case of timeout accumulator until a timeout really happened
            else:
                accumulatorDict = self._getAccumulator(name)
                powerCalculated = False

                # "autoReset": in absolute case given power level is not allowed to be less than previous given power level except autoReset has been set, in that case power will be used as new reference power but calculated energy will stay at its level and not be reset, too
                if (power is not None) and (power < accumulatorDict["referencePower"]) and accumulatorDict["absolute"]:
                    if accumulatorDict["autoReset"]:
                        # reset reference power value and process given power value with calculatePower()
                        accumulatorDict["referencePower"] = 0
                    else:
                        raise Exception(f"in absolute case given power {power} cannot be less than previous power {accumulatorDict['referencePower']} except autoReset is set to True, but autoReset is {accumulatorDict['autoReset']}")

                # timeout: accumulator with timeout detected
                if accumulatorDict["timerName"]:
                    calculatePower(accumulatorName = name, power = power, timeStamp = currentTime)
                    powerCalculated = True      # remember power value has been processed
                    resetMinMaxValues = True    # only reset position where min, max, overallSum and valueCounter values have to be reset

                    if (accumulatorDict["calls"] and self.counter(accumulatorDict["timerName"])) or (not accumulatorDict["calls"] and self.timer(accumulatorDict["timerName"])):
                        returnValue = accumulatorDict["calculatedEnergy"]

                        # timeout happened, some values have to be reset
                        accumulatorDict["calculatedEnergy"] = 0
                        if accumulatorDict["multiplyTime"]:
                            accumulatorDict["referenceTime"] = currentTime   # else it stays None
                    #else:
                    #    returnValue = None      # return None in case of timeout accumulator until a timeout really happened

                # power not processed so far, so process it now
                if not powerCalculated:
                    calculatePower(accumulatorName = name, power = power, timeStamp = currentTime)
                    returnValue = accumulatorDict["calculatedEnergy"]
                    powerCalculated = True      # remember power value has been processed

            #Supporter.debugPrint(f"name: {name}, sum:{accumulatorDict['calculatedEnergy']}, ref:{accumulatorDict['referencePower']}, ret:{returnValue}, power:{power}", color = "RED", borderSize = 0)

            if returnValue is not None and accumulatorDict["valueCounter"]:
                returnValue = {"acc" : returnValue, "min" : accumulatorDict["minimum"], "max" : accumulatorDict["maximum"], "avg" : accumulatorDict["overallSum"] / accumulatorDict["valueCounter"]}

                # min, max, overallSum and valueCounter was still needed here to calculate the return value but now they have to be cleared in reset case
                if resetMinMaxValues and accumulatorDict["valueCounter"] is not None:
                    accumulatorDict["minimum"] = None
                    accumulatorDict["maximum"] = None
                    accumulatorDict["overallSum"] = None
                    accumulatorDict["valueCounter"] = 0     # if accumulatorDict["valueCounter"] is not None then minMaxAverage has been set to True during setup! 

            return returnValue


        # if timeStamp is None take current time
        currentTime = Supporter.getTimeStamp()

        # is there a list of strings to be handled or just a single string?
        if type(name) == list:
            returnValue = {}

            for entry in name:
                if type(timeout) == dict:
                    # take the timeout given for the current accumulator entry if exist, otherwise timeout is None
                    if entry in timeout:
                        entryTimeout = timeout[entry]
                    else:
                        entryTimeout = None
                else:
                    # all accumulators get the same timeout since only one timeout has been given and it wasn't specified for what accumulator is should be used
                    entryTimeout = timeout
                    
                if result := handleAccumulator(name = entry, power = power, timeout = entryTimeout, currentTime = currentTime, synchronized = synchronized, useCounter = useCounter, multiplyTime = multiplyTime, absolute = absolute, reSetup = reSetup, autoReset = autoReset, minMaxAverage = minMaxAverage):
                    returnValue[entry] = result
        else:
            returnValue = handleAccumulator(name = name, power = power, timeout = timeout, currentTime = currentTime, synchronized = synchronized, useCounter = useCounter, multiplyTime = multiplyTime, absolute = absolute, reSetup = reSetup, autoReset = autoReset, minMaxAverage = minMaxAverage)

        return returnValue

