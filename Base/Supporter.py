'''
'''
import time
import calendar


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
    def getCounterValue(self, name : str):
        counterName = "__counter_" + name

        # setup counter in global namespace if necessary
        nameSpace = globals()
        if counterName not in nameSpace:
            return 0
        else:
            return nameSpace[counterName]
        

    @classmethod
    def counter(self, name : str, value : int = 0, freeRunning : bool = False, autoReset : bool = False, singularTrue : bool = False):
        '''
        Simple counter returns True if counter is equal to or greater than given value
        
        With each call it counts up (first call starts with 1)

        autoReset will reset counter when given value has been reached
        singularTrue will return True only when the given value is equal to given counter but not if it is greater than it
        a freeRunning counter will never return with True but just count up, use getCounterValue to read value
        '''
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
            # auto reset value if given
            if autoReset:
                value = 0
                       
            # return True if "counter == value" or in case "counter > value" only if singularTure has not been given, otherwise return False
            return not singularTrue or nameSpace[counterName] == value 
        
        return False

