#!/usr/bin/env python3


'''
ATTENTION:
- class variables should always be named that way:
    __<variableName>_always_use_getters_and_setters
    - Python will transform then into _<class>__<variableName>_always_use_getters_and_setters, so they will get maximum prevented from misusage  
    - reason is that a variable cls.abc is identical to self.abc until you set self.abc to something than you really have two different variables cls.abc and self.abc!!!
- @todo add further good practice here!



@todo interfaces fehlen noch komplett
@todo alle todos suchen
@todo alle xxxxx suchen





object
+---Crc
+---InterfaceFactory
+---ProjectRunner
+---Supporter
+---Base
    +---MqttBase
        +---ThreadBase
            +---ThreadObject
            |   +---InterfaceBase
            |   |   +---DummyInterface                  (to be used as template to create interfaces)
            |   |   +---MqttBrokerInterface
            |   |   +---TcpInterface
            |   |   |   +---EasyMeterTcpInterface
            |   |   +---EffektaUartInterface
            |   |   +---UartInterface
            |   +---EasyMeter
            |   +---SignalMessenger
            |   +---MqttBridge
            |   +---WatchDog
            |   +---Worker                              (to be used as template for an own worker thread)
            |       +---PowerPlant
            +---EffektaController                       ?????
            +---Logger
                +---LoggerOverwrite                     (to be used as template to overwrite Logger)
                






'''


import argparse
import sys


from Base.ProjectRunner import ProjectRunner
import Logger.Logger
from Base.MqttBase import MqttBase


'''
project main function
'''
if __name__ == '__main__':
    initFileName = "init.json"
    logLevel     = Logger.Logger.Logger.LOG_LEVEL.INFO.value
    logFilter    = r""
    stopAfterSeconds = 0
    printAlways = False
    writeLogToDiskWhenEnds = False
    missingImportMeansError = False

    # handle command line arguments
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("-i", "--init",                 default = initFileName,            dest = "initFileName",           type = str,                      help = "use this init file instead of init.json")
    argumentParser.add_argument("-l", "--loglevel",             default = logLevel,                dest = "logLevel",               type = int,                      help = "log level 5..0, 5 = all (default = 3)")
    argumentParser.add_argument("-f", "--logFilter",            default = logFilter,               dest = "logFilter",              type = str,                      help = "log filter regex, only messages from matching threads will be logged except error and fatal messages")
    argumentParser.add_argument("-s", "--stop-after",           default = stopAfterSeconds,        dest = "stopAfterSeconds",       type = int,                      help = "for development only, all threads will be teared down after this amount of seconds (default = -1 = endless)")
    argumentParser.add_argument("-p", "--print-always",         default = printAlways,             dest = "printAlways",                        action='store_true', help = "for development only, log messages will always be printed to screen, usually this will be done only in debug case")
    argumentParser.add_argument("-w", "--write-when-ends",      default = writeLogToDiskWhenEnds,  dest = "writeLogToDiskWhenEnds",             action='store_true', help = "always write log buffer to disk when program comes to an end not only in error case")
    argumentParser.add_argument("-e", "--missing-import-error", default = missingImportMeansError, dest = "missingImportMeansError",            action='store_true', help = "an exception will be thrown if an @import file in init file doesn't exist, otherwise it's only printed to stdout")
    arguments = argumentParser.parse_args()

    stopReason = ProjectRunner.executeProject(arguments.initFileName, arguments.logLevel, arguments.logFilter, arguments.stopAfterSeconds, arguments.printAlways, arguments.writeLogToDiskWhenEnds, arguments.missingImportMeansError)

    Logger.Logger.Logger.trace("__main__", "finito [" + Logger.Logger.Logger.get_projectName() + "]" + (" : " + stopReason) if len(stopReason) else "")

