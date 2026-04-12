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
    _SIMULATE = False           # to be set to True as soon as at least one of the objects are simulating values, this will prevent the external watchdog relay from being triggered
    _SIMULATION_ALLOWED = False  

    _STARTUP_PHASE = True       # has to be set to False when all threads are up and running


    @classmethod
    def getStartupPhase(cls) -> bool:
        '''
        Get current startup phase, True means still starting, False means starting all threads has been finished
        '''
        return Base._STARTUP_PHASE


    @classmethod
    def clearStartupPhase(cls):
        '''
        To be called when starting all threads has been finished
        '''
        if not cls.getStartupPhase():
            Logger.Logger.Logger.get_logger().warning(Supporter.getCaller(), f"startup phase already cleared!")
        Base._STARTUP_PHASE = False


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


    def tagsIncluded(self, tagNames : list, intIfy : bool = False, optional : bool = False, configuration : dict = None, default = None, valueType = None) -> bool:
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

        # if string and not list has been given convert it to list
        if type(tagNames) != type([]):
            if type(tagNames) == type(""):
                tagNames = [tagNames]
            else:
                raise Exception(f"type of tagNames is {type(tagNames)} what is not supported, only list or str")

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
            else:
                if intIfy:
                    configuration[tagName] = int(configuration[tagName])                # this will ensure that value contains a valid int even if it has been given as string (what is common in json!)
                if valueType is not None:
                    if valueType != type(configuration[tagName]):
                        raise Exception(f"element {tagName} is not of type {valueType} but of type {type(configuration[tagName])}")

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
                    # timer doesn't exist or reSetup has been given so use "timerName" because "existingTimerName" could be None
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


    def accumulator(self, name : str, value, period : int = None, absolute : bool = False, multiplyTime : bool = False, maxRefAge : int = None, timeValue : float = None, convert : float = None):
        '''
        To create and handle a power accumulator that gets power values (or any other kind of values that have to be accumulated) and adds them optionally multiplied by their duration times
        If the accumulator is set up for absolute calculation an initial power value can be given if the initial reference value is not 0
        The accumulator can be used to accumulate not only power values, other values can be accumulated, too!

        @param name                 name of the power accumulator that will be created in current name space
        @param value                power value that has to be accumulated
                                    the first given value will be used as reference if necessary
        @param period               period of time during that values will be hold, older ones will be thrown away
                                    this value is only needed for setup and will be ignored during all other calls
        @param absolute             if only absolute values are available, e.g. absolute energy values, by subtracting the predecessor value the relative value can be calculated, what is usually the typical use case
                                    this value is only needed for setup and will be ignored during all other calls
        @param multiplyTime         if there are only e.g. power values but energy values will be needed it's possible to multiply the given value with the time since the previous value has been given and multiply power with that time value, so if Watt has been given the calculated value will be in Ws
                                    this value is only needed for setup and will be ignored during all other calls
        @param maxRefAge            older values will be removed but the newest one of them will be used as new reference value, if too old references should not be taken a maximum age for the reference can be given here, e.g. 100 will take a reference if it is not older than "100s + period"
                                    this value is only needed for setup and will be ignored during all other calls
        @param timeValue            usually not needed since current time in seconds is used as timestamp but especially for debugging it's useful to give own time values
        @param convert              a value can be given that is multiplied with the final result, so e.g. if you af a unit of "kWh/4" and time is always in seconds you can convert "W" be giving (1000 * 60 * 60) / (15 * 60)
        @return                     returns the amount of calculated energy so far, to read energy value only the given power should be 0
        '''
        VALUE_INDEX = 0
        TIME_INDEX = 1

        if type(name) != str or len(name) == 0:
            raise Exception(f"Accumulator needs a name!")

        if not self.accumulatorExists(name):
            if period is None:
                raise Exception("Accumulator needs a period to be set up")

            # create new accumulator
            self._createAccumulator(name, {
                "values"        : [],            # contains all data values and time stamps
                "reference"     : None,          # reference value, needed for absolute values (delta to predecessor has to be calculated) and in case multiplyTime (delta time to predecessor has to be calculated)
                "period"        : period,
                "absolute"      : absolute,
                "multiplyTime"  : multiplyTime,
                "maxRefAge"     : maxRefAge,
            })
        accumulatorDict = self._getAccumulator(name) 

        if timeValue is None:
            timeValue = Supporter.getTimeStamp()

        # add new value
        accumulatorDict["values"].append([value, timeValue])

        # if oldest value is older than period a cleanup and set new reference is necessary 
        if accumulatorDict["values"][0][TIME_INDEX] <= (timeValue - accumulatorDict["period"]):         # oldest value outside given period
            newValues = []
            for entry in accumulatorDict["values"]:
                if entry[TIME_INDEX] <= (timeValue - accumulatorDict["period"]):
                    accumulatorDict["reference"] = entry        # remember new reference, entry will not be longer in the values list
                else:
                    newValues.append(entry)                     # entry is still in the values list
            accumulatorDict["values"] = newValues

        # if reference is None oldest value will become reference
        if accumulatorDict["reference"] is None:
            accumulatorDict["reference"] = accumulatorDict["values"][0]

        # if reference is too old a new referencing is necessary
        if maxRefAge is not None:
            if accumulatorDict["values"][-1][TIME_INDEX] - accumulatorDict["reference"][TIME_INDEX] - accumulatorDict["period"] > maxRefAge:
                accumulatorDict["reference"] = accumulatorDict["values"][0]     # oldest value will become the new reference, since previous reference was too old

        # calculate sum
        sum = 0
        previousEntry = accumulatorDict["reference"]
        if absolute:
            entry = accumulatorDict["values"][-1]                                                       # for absolute values we need just the newest one
            multiplyer = 1 if not multiplyTime else entry[TIME_INDEX] - previousEntry[TIME_INDEX]       # multiplyer = time delta since previous entry
            sum = (entry[VALUE_INDEX] - previousEntry[VALUE_INDEX]) * multiplyer
        else:
            for entry in accumulatorDict["values"]:
                multiplyer = 1 if not multiplyTime else entry[TIME_INDEX] - previousEntry[TIME_INDEX]        # multiplyer = time delta since previous entry

                sum += entry[VALUE_INDEX] * multiplyer

                previousEntry = entry

        if (len(accumulatorDict["values"]) == 1) and (accumulatorDict["values"][0] == accumulatorDict["reference"]) and (multiplyTime or absolute):
            # to set accumulatorDict["reference"] = accumulatorDict["values"][0] makes things much easier but if the reference value is identical with the only stored value and it's used because of "absolute" or "multiplyTime" then None should be returned instead of 0 because otherwise it's not possible for a caller to decide if the energy sum is 0 or is unknown
            sum = None

        if (convert is not None) and (sum is not None):
            sum *= convert

        return sum

