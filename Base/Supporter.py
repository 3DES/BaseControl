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
        return leftEnclosing + str(string) + rightEnclosing


    @classmethod
    def getTimeStamp(cls):
        return calendar.timegm(time.gmtime())

