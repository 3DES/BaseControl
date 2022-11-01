#!/usr/bin/python3


'''
ATTENTION:
- class variables should always be named that way:
    __<variableName>_always_use_getters_and_setters
    - Python will transform then into _<class>__<variableName>_always_use_getters_and_setters, so they will get maximum prevented from misusage  
    - reason is that a variable cls.abc is identical to self.abc until you set self.abc to something than you really have two different variables cls.abc and self.abc!!!
- @todo add further good practice here!



@todo in ProjectRunner alle globalen Variablen ggf. umbenennen nach "__xxx"?
@todo timestamp in logger einbauen
@todo interfaces fehlen noch komplett
@todo alle todos suchen
@todo alle xxxxx suchen


'''


import argparse
import sys


from Base.ProjectRunner import ProjectRunner
import Logger.Logger
from Base.MqttBase import MqttBase


#import time
#from Base.Supporter import Supporter
#value1 = Supporter.counter("B", 2, autoReset = True)
#value1 = Supporter.counter("B", 2, autoReset = True)
#value1 = Supporter.counter("B", 2, autoReset = True)
#value1 = Supporter.counter("B", 2, autoReset = True)
#value1 = Supporter.counter("B", 2, autoReset = True)
#
#while True:
#    value1 = Supporter.counter("B", 2, autoReset = True)
#    value2 = Supporter.counter("B", 2, autoReset = True, dontCount = True)
#    value3 = Supporter.counter("B", 2, autoReset = True, getValue = True, dontCount = True)
#    print(str(value1) + " " + str(value2) + " " + str(value3) + " ")
#
#sys.exit(255)
#startTime = Supporter.getTimeStamp()
#for x in range(20):
#    print(str(Supporter.getTimeStamp() - startTime) + " seconds: ", end = "")
#    if (Supporter.timer(name = "A", timeout = 2, strict = True)):
#        print("over now")
#    else:
#        print("not yet")
#    time.sleep(3)
#Supporter.timer(name = "A", timeout = 3)
#Supporter.timer(name = "A")
#Supporter.timer(name = "A", remove = True)
#Supporter.timer(name = "A", timeout = 3)
#Supporter.timer(name = "A")


'''
project main function
'''
if __name__ == '__main__':
    initFileName = "init.json"
    logLevel     = Logger.Logger.Logger.LOG_LEVEL.INFO.value
    stopAfterSeconds = 0
    printAlways = False
    writeLogToDiskWhenEnds = False

    # handle command line arguments
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("-i", "--init",            default = initFileName,           dest = "initFileName",           type = str,                      help = "use this init file instead of init.json")
    argumentParser.add_argument("-l", "--loglevel",        default = logLevel,               dest = "logLevel",               type = int,                      help = "log level 5..0, 5 = all (default = 3)")
    argumentParser.add_argument("-s", "--stop-after",      default = stopAfterSeconds,       dest = "stopAfterSeconds",       type = int,                      help = "for development only, all threads will be teared down after this amount of seconds (default = -1 = endless)")
    argumentParser.add_argument("-p", "--print-always",    default = printAlways,            dest = "printAlways",                        action='store_true', help = "for development only, log messages will always be printed to screen, usually this will be done only in debug case")
    argumentParser.add_argument("-w", "--write-when-ends", default = writeLogToDiskWhenEnds, dest = "writeLogToDiskWhenEnds",             action='store_true', help = "always write log buffer to disk when program comes to an end not only in error case")
    arguments = argumentParser.parse_args()

    stopReason = ProjectRunner.executeProject(arguments.initFileName, arguments.logLevel, arguments.stopAfterSeconds, arguments.printAlways, arguments.writeLogToDiskWhenEnds)

    print("finito [" + Logger.Logger.Logger.get_projectName() + "]" + (" : " + stopReason) if len(stopReason) else "")

