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


'''
project main function
'''
if __name__ == '__main__':
    initFileName  = "init.json"
    logLevel      = Logger.Logger.Logger.LOG_LEVEL.INFO.value
    logFilter     = r""
    stopAfterSeconds = 0
    writeLogToDiskWhenEnds = False
    missingImportMeansError = False
    jsonDump = False
    jsonDumpFilter = "user|password|\+49"     # default filter
    logFileName = "logger.txt"

    # collect command line and print it in re-usable format
    commandLine = " ".join("'" + parameter + "'" for parameter in sys.argv)
    print(f"command line parameters: {commandLine}")

    # handle command line arguments
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("-i", "--init",                 default = initFileName,            dest = "initFileName",           type = str,                      help = "use this init file instead of init.json")
    argumentParser.add_argument("-l", "--log-level",            default = logLevel,                dest = "logLevel",               type = int,                      help = "log level 5..0, 5 = all (default = 3)")
    argumentParser.add_argument("-L", "--log-file",             default = logFileName,             dest = "logFileName",            type = str,                      help = "use this log file instead of logger.txt")
    argumentParser.add_argument("-f", "--log-filter",           default = logFilter,               dest = "logFilter",              type = str,                      help = "log filter regex, only messages from matching threads will be logged except error and fatal messages")
    argumentParser.add_argument("-s", "--stop-after",           default = stopAfterSeconds,        dest = "stopAfterSeconds",       type = int,                      help = "for development only, all threads will be teared down after this amount of seconds (default = -1 = endless)")
    argumentParser.add_argument("-p", "--print-log-level",      default = None,                    dest = "printLogLevel",          type = int,                      help = "up to which level log entries should be printed onto screen")
    argumentParser.add_argument("-w", "--write-when-ends",      default = writeLogToDiskWhenEnds,  dest = "writeLogToDiskWhenEnds",             action='store_true', help = "always write log buffer to disk when program comes to an end not only in error case")
    argumentParser.add_argument("-e", "--missing-import-error", default = missingImportMeansError, dest = "missingImportMeansError",            action='store_true', help = "an exception will be thrown if an @import file in init file doesn't exist, otherwise it's only printed to stdout")
    argumentParser.add_argument("-d", "--remote-debug",                                            dest = "remoteDebugging",                    action='store_true', help = "remote debugging is enabled and it's expected that the debug server is up and running")
    argumentParser.add_argument("--SIMULATE",                   default = False,                   dest = "simulate",                           action='store_true', help = "if this is not set all SIMULATE flags in json files will be ignored")
    argumentParser.add_argument("--json-dump",                  default = False,                   dest = "jsonDump",                           action='store_true', help = "dumps json configuration after read all files recursively")
    argumentParser.add_argument("--json-dump-filter",           default = None,                    dest = "jsonDumpFilter",         type = str,                      help = "replaces values that match this regex or values whose keys match this regex with #####, default if not given is {jsonDumpFilter}")
    argumentParser.add_argument("--json-dump-filter-none",      default = None,                    dest = "jsonDumpFilterNone",                 action='store_true', help = "to suppress default value for jsonDumpFilter")

    arguments = argumentParser.parse_args()

    if arguments.remoteDebugging:
        from pydevd_file_utils import setup_client_server_paths
        MY_PATHS_FROM_ECLIPSE_TO_PYTHON = [('//HOMEASSISTANT/share/PowerPlant', '/share/PowerPlant'),]
        setup_client_server_paths(MY_PATHS_FROM_ECLIPSE_TO_PYTHON)
        import pydevd
        pydevd.settrace("debugserver", port = 5678, suspend = False)   # additional parameters: stdoutToServer=True, stderrToServer=True / debugserver should be set in /etc/hosts file, e.g. "192.168.168.9   debugserver"

    # print log level has to be less or equal to log level
    if arguments.printLogLevel is None:
        arguments.printLogLevel = Logger.Logger.Logger.LOG_LEVEL.NONE.value
    elif (arguments.printLogLevel is not None) and (arguments.printLogLevel > arguments.logLevel):
        arguments.printLogLevel = arguments.logLevel

    if arguments.jsonDumpFilter is not None:
        if len(arguments.jsonDumpFilter) == 0:
            # empty parameter given so use None
            arguments.jsonDumpFilter = None
    elif not arguments.jsonDumpFilterNone:
        # parameter not given, and --json-dump-filter-none also not given, so use default case
        arguments.jsonDumpFilter = jsonDumpFilter

    print(f"dump filter is {arguments.jsonDumpFilter}")

    stopReason = ProjectRunner.executeProject(
        initFileName            = arguments.initFileName,
        logFileName             = arguments.logFileName,
        logLevel                = arguments.logLevel,
        printLogLevel           = arguments.printLogLevel,
        logFilter               = arguments.logFilter,
        stopAfterSeconds        = arguments.stopAfterSeconds,
        writeLogToDiskWhenEnds  = arguments.writeLogToDiskWhenEnds,
        missingImportMeansError = arguments.missingImportMeansError,
        jsonDump                = arguments.jsonDump,
        jsonDumpFilter          = arguments.jsonDumpFilter,
        additionalLeadIn        = commandLine,
        simulationAllowed       = arguments.simulate)

    Logger.Logger.Logger.trace("__main__", "finito [" + Logger.Logger.Logger.get_projectName() + "]" + (" : " + stopReason) if len(stopReason) else "")

