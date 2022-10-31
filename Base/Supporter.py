'''
'''
import time
import calendar
import pydoc


class Supporter(object):
    '''
    classdocs
    '''


    @classmethod
    def encloseString(cls, string, leftEnclosing : str = "[", rightEnclosing : str = "]"):
        '''
        formats given string by enclosing it in given left and right enclosing string, e.g.
            FOOBAR -->  [FOOBAR]
        '''
        return leftEnclosing + str(string) + rightEnclosing


    @classmethod
    def getTimeStamp(cls):
        return calendar.timegm(time.gmtime())


    @classmethod
    def getDeltaTime(cls, timeStamp : int):
        return cls.getTimeStamp() - timeStamp


    @classmethod
    def getCounterValue(cls, name : str):
        counterName = "__counter_" + name

        # setup counter in global namespace if necessary
        nameSpace = globals()
        if counterName not in nameSpace:
            return 0
        else:
            return nameSpace[counterName]
        

    @classmethod
    def counter(cls, name : str, value : int = 0, freeRunning : bool = False, autoReset : bool = False, singularTrue : bool = False):
        '''
        Simple counter returns True if counter is equal to or greater than given value
        
        With each call it counts up (first call starts with 1)

        autoReset will reset counter when given value has been reached
        singularTrue will return True only when the given value is equal to given counter but not if it is greater than it
        a freeRunning counter will never return with True but just count up, use getCounterValue to read value
        '''
        result = False
        
        counterName = "__counter_" + name

        # setup counter in global namespace if necessary
        nameSpace = globals()
        if counterName not in nameSpace:
            nameSpace[counterName] = 0       # create local variable with name given in string

        # stop counting up when value + 1 has been reached (otherwise counter would count up endless)
        if nameSpace[counterName] <= value or freeRunning:
            nameSpace[counterName] += 1

        # given value reached?
        if nameSpace[counterName] >= value and not freeRunning:
            # return True if "counter == value" or in case "counter > value" only if singularTure has not been given, otherwise return False
            result = (not singularTrue) or (nameSpace[counterName] == value)

            # auto reset value if given
            if autoReset:
                nameSpace[counterName] = 0

        return result


    @classmethod
    def timer(cls, name : str, timeout : int = 0, startTime : int = 0):
        # @todo startTime noch unterstuetzen!!!
        '''
        Simple timer returns True if given timeout has been reached or exceeded
        
        A timeout value of 0 will not setup a not existing timer but can be used to check a running timer and reset it if it exceeded, the original period will not be changed
        A timeout different from 0 will setup a new timer if it doesn't exist or set a new time period if timeout is different but the current set time will not be changed

        The timer can jitter (depending on your read timing) but it will never drift away!
        '''
        #        def updateTime(startTime : int, currentTime : int, period : int):
        #            '''
        #            Internal method to do the timer math
        #            '''
        #            if currentTime < startTime + timeout:
        #                return startTime + timeout
        #            else:
        #                # do some math... without importing math
        #                # this works, e.g.  17 + (42 // 7 + (42 % 7 > 0)) * 7, with:
        #                #  17 = old timestamp
        #                #  42 = delta time
        #                #   7 = timeout
        #                deltaTime = currentTime - startTime
        #                return startTime + (((deltaTime // timeout) + (deltaTime % timeout > 0)) * timeout)
        result = False
        
        timerName = "__timer_" + name

        # setup counter in global namespace if necessary
        nameSpace = globals()
        if (timerName not in nameSpace) and (timeout > 0):
            nameSpace[timerName] = [cls.getTimeStamp() + timeout, timeout]      # create local variable with name given in string
        elif timeout > 0:
            nameSpace[timerName][1] = timeout                                   # change period for next interval only

        currentTime = cls.getTimeStamp()
        if currentTime > nameSpace[timerName][0]:
            deltaTime = currentTime - nameSpace[timerName][0]
            
            if currentTime < nameSpace[timerName][0] + nameSpace[timerName][1]:
                nameSpace[timerName][0] += nameSpace[timerName][1]
            else:
                # do some math... without importing math
                # this works, e.g.  17 + (42 // 7 + (42 % 7 > 0)) * 7, with:
                #  17 = old timestamp
                #  42 = delta time
                #   7 = timeout
                nameSpace[timerName][0] += (((deltaTime // nameSpace[timerName][1]) + (deltaTime % nameSpace[timerName][1] > 0)) * nameSpace[timerName][1])
            return True
        else:
            return False 


    @classmethod
    def loadClassFromFile(cls, fullClassName : str):
        '''
        loads a class from a given file
        no object will be created only the class will be loaded and given back to caller

        :param fullClassName: name of the class including package and module to be loaded (e.g. Logger.Logger.Logger means Logger class contained in Logger.py contained in Logger folder)
        :return: loaded but not yet instantiated class
        :rtype: module
        :raises Exception: if given module doesn't exist
        '''
        className = fullClassName.rsplit('.')[-1]
        classType = ".".join(fullClassName.rsplit('.')[0:-1])
        loadableModule = pydoc.locate(classType)

        if loadableModule is None:
            raise Exception("there is no module \"" + classType + "\"")

        print("loading: module = " + str(loadableModule) + ", className = " + str(className) + ", classType = " + str(classType))
        loadableClass = getattr(loadableModule, className)
        return loadableClass


