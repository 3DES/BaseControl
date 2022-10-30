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


#print(MqttBase.validateTopicFilter("#"))
#print(MqttBase.validateTopicFilter("a/b/#"))
#print(MqttBase.validateTopicFilter("a/+/b"))
#print(MqttBase.validateTopicFilter("a/+/b/+/c"))
#print(MqttBase.validateTopicFilter("a/+/b/+"))
#print(MqttBase.validateTopicFilter(""))
#print(MqttBase.validateTopicFilter("/"))
#print(MqttBase.validateTopicFilter("a/+b#"))
#print(MqttBase.validateTopicFilter("a/##b"))
#print(MqttBase.validateTopicFilter("#/a/b"))
#print(MqttBase.validateTopicFilter("a/b/"))
#print("---------")
#for filter in ("a/b/#", "a/b/+", "a/+/c/+/e"):
#    filter = MqttBase.splitTopic(filter)
#    print(MqttBase.matchTopic("a/b/c",     filter))
#    print(MqttBase.matchTopic("a/b",       filter))
#    print(MqttBase.matchTopic("a/b/c/d",   filter))
#    print(MqttBase.matchTopic("a/b/c/d/e", filter))
#    print(MqttBase.matchTopic("a/a/c/a/e", filter))
#    print(MqttBase.matchTopic("a",         filter))
#    print("--")
#sys.exit(255)


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

    ProjectRunner.executeProject(arguments.initFileName, arguments.logLevel, arguments.stopAfterSeconds, arguments.printAlways, arguments.writeLogToDiskWhenEnds)

