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


from Base.ProjectRunner import ProjectRunner
import Logger.Logger


'''
project main function
'''
if __name__ == '__main__':
    initFileName = "init.json"
    logLevel     = Logger.Logger.Logger.LOG_LEVEL.INFO.value
    stopAfterSeconds = 0

    # handle command line arguments
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("-i", "--init",       default = initFileName,     dest = "initFileName",                 help = "use this init file instead of init.json")
    argumentParser.add_argument("-l", "--loglevel",   default = logLevel,         dest = "logLevel",         type = int, help = "log level 5..0, 5 = all (default = 3)")
    argumentParser.add_argument("-s", "--stop-after", default = stopAfterSeconds, dest = "stopAfterSeconds", type = int, help = "for development only, all threads will be teared down after this amount of seconds (default = -1 = endless)")
    arguments = argumentParser.parse_args()

    ProjectRunner.executeProject(arguments.initFileName, arguments.logLevel, arguments.stopAfterSeconds)

