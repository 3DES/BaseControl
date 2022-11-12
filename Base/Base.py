from Base.Supporter import Supporter


class Base(object):
    '''
    classdocs
    '''


    def __init__(self, baseName : str, configuration : dict):
        '''
        Constructor
        '''
        self.name = baseName                                                # set name for this thread
        self.configuration = configuration                                  # remember given configuration


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
        counterName = f"{self.name}_{name}"
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


    def timer(self, name : str, timeout : int = 0, startTime : int = 0, remove : bool = False, strict : bool = False, setup : bool = False, remainingTime : bool = False, firstTimeTrue : bool = False):
        '''
        Simple timer returns True if given timeout has been reached or exceeded
        
        A timeout value of 0 will not setup a not existing timer but can be used to check a running timer and reset it if it exceeded, the original period will not be changed
        A timeout different from 0 will setup a new timer if it doesn't exist or set a new time period if timeout is different but the current set time will not be changed

        The timer can jitter (depending on your read timing) but it will never drift away!

        If startTime is not given current time will be taken, if startTiem has been given it will only be taken to setup the timer but will be ignored if the timer is already running, so a timer can be set up and checked with the same line of code
        
        If remove is True the timer will be deleted
        
        If strict is True an Exception will be thrown in case more than one timeout period has passed over since last call, so calling is too slow and timeout events have been lost
        
        If setup is True timer will be set up even if it already exists, but remove has higher priority if also given, in that case no new timer will be set up!
        
        If remainingTime is True timer handling is as usual but the remaining time will be given back instead of True or False, check can be done by comparing the returned value with 0, a positive value (= False) means there is still some time left, a negative value (= True) means time is already over 

        During setup call the timer usually returns with False but if firstTimeTrue is set to True it will return with True for the first time, so it's not necessary to handle it manually to get informed at setup call, too and not only for all following periods
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

        setupTurn = False
        timerName = f"{self.name}_{name}"
        nameSpace = globals()

        if remove:
            if timerName not in nameSpace:
                raise Exception("timer " + timerName + " cannot be deleted since it doesn't exist")
            del(nameSpace[timerName])
            return True
        else:
            # setup counter in global namespace if necessary
            if timeout > 0:
                if (timerName not in nameSpace) or setup:
                    if startTime == 0:
                        startTime = Supporter.getTimeStamp()                            # startTime is needed, if it hasn't been given take current time instead
                    nameSpace[timerName] = [updateTime(startTime, timeout), timeout]    # create local variable with name given in string
                    setupTurn = True                                                    # timer has been setup in this call
                else:
                    nameSpace[timerName][1] = timeout                                   # update timer period for following interval but not for the currently running one
            elif timerName not in nameSpace:
                raise Exception("a timer cannot be set up with a timeout of 0")

            currentTime = Supporter.getTimeStamp()
            if currentTime >= nameSpace[timerName][0]:                                   # timeout happened?
                originalTimeout = nameSpace[timerName][0]
                nameSpace[timerName][0] = updateTime(nameSpace[timerName][0], nameSpace[timerName][1])

                if strict:
                    deltaTime = nameSpace[timerName][0] - originalTimeout
                    if deltaTime != nameSpace[timerName][1]:    # delta must be 1 period otherwise throw exception
                        raise Exception("Timer has been polled too slowly so more than one timeout period passed over and some events have been missed, event happened occurred " + str(deltaTime) + " seconds ago")
                if remainingTime:
                    return originalTimeout - currentTime
                else:
                    return True
            else:
                if remainingTime:
                    return nameSpace[timerName][0] - currentTime
                else: 
                    return False or (setupTurn and firstTimeTrue)

