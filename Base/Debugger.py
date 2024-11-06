import time
import sys
import Base         # needed to access variables from threads
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter
from Logger.Logger import Logger
import re
import numbers


class Debugger(ThreadObject):
    '''
    classdocs
    '''
    threadDictionary = None

    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration, interfaceQueues)
        self.logger.info(self, "init (Debugger)")

        # there are three test variables that can be used to understand how things are working here...
        #
        # global variable     | class variable            | object variable       | delete global variable     | delete class variable            | delete object variable                 
        # --------------------+---------------------------+-----------------------+----------------------------+----------------------------------+----------------------
        # test,global         | Debugger.test,cls         | Debugger.test         | test,global,delete         | Debugger.test,cls,delete         | Debugger.test,delete        
        # test.a,global       | Debugger.test.a,cls       | Debugger.test.a       | test.a,global,delete       | Debugger.test.a,cls,delete       | Debugger.test.a,delete      
        # test.b,global       | Debugger.test.b,cls       | Debugger.test.b       | test.b,global,delete       | Debugger.test.b,cls,delete       | Debugger.test.b,delete      
        # test.b.c,global     | Debugger.test.b.c,cls     | Debugger.test.b.c     | test.b.c,global,delete     | Debugger.test.b.c,cls,delete     | Debugger.test.b.c,delete    
        # test.d,global       | Debugger.test.d,cls       | Debugger.test.d       | test.d,global,delete       | Debugger.test.d,cls,delete       | Debugger.test.d,delete      
        # test.d.0,global     | Debugger.test.d.0,cls     | Debugger.test.d.0     | test.d.0,global,delete     | Debugger.test.d.0,cls,delete     | Debugger.test.d.0,delete    
        # test.d.1,global     | Debugger.test.d.1,cls     | Debugger.test.d.1     | test.d.1,global,delete     | Debugger.test.d.1,cls,delete     | Debugger.test.d.1,delete    
        # test.d.2,global     | Debugger.test.d.2,cls     | Debugger.test.d.2     | test.d.2,global,delete     | Debugger.test.d.2,cls,delete     | Debugger.test.d.2,delete    
        # test.d.3,global     | Debugger.test.d.3,cls     | Debugger.test.d.3     | test.d.3,global,delete     | Debugger.test.d.3,cls,delete     | Debugger.test.d.3,delete    
        # test.d.3.0,global   | Debugger.test.d.3.0,cls   | Debugger.test.d.3.0   | test.d.3.0,global,delete   | Debugger.test.d.3.0,cls,delete   | Debugger.test.d.3.0,delete  
        # test.d.3.1,global   | Debugger.test.d.3.1,cls   | Debugger.test.d.3.1   | test.d.3.1,global,delete   | Debugger.test.d.3.1,cls,delete   | Debugger.test.d.3.1,delete  
        # test.d.4,global     | Debugger.test.d.4,cls     | Debugger.test.d.4     | test.d.4,global,delete     | Debugger.test.d.4,cls,delete     | Debugger.test.d.4,delete    
        # test.d.4.g,global   | Debugger.test.d.4.g,cls   | Debugger.test.d.4.g   | test.d.4.g,global,delete   | Debugger.test.d.4.g,cls,delete   | Debugger.test.d.4.g,delete  
        # test.d.4.g.0,global | Debugger.test.d.4.g.0,cls | Debugger.test.d.4.g.0 | test.d.4.g.0,global,delete | Debugger.test.d.4.g.0,cls,delete | Debugger.test.d.4.g.0,delete
        # test.d.4.g.1,global | Debugger.test.d.4.g.1,cls | Debugger.test.d.4.g.1 | test.d.4.g.1,global,delete | Debugger.test.d.4.g.1,cls,delete | Debugger.test.d.4.g.1,delete
        # test.d.4.h.0,global | Debugger.test.d.4.h.0,cls | Debugger.test.d.4.h.0 | test.d.4.h.0,global,delete | Debugger.test.d.4.h.0,cls,delete | Debugger.test.d.4.h.0,delete
        # test.d.4.h.1,global | Debugger.test.d.4.h.1,cls | Debugger.test.d.4.h.1 | test.d.4.h.1,global,delete | Debugger.test.d.4.h.1,cls,delete | Debugger.test.d.4.h.1,delete
        # test.d.4.h.2,global | Debugger.test.d.4.h.2,cls | Debugger.test.d.4.h.2 | test.d.4.h.2,global,delete | Debugger.test.d.4.h.2,cls,delete | Debugger.test.d.4.h.2,delete
        # test.e and f,global | Debugger.test.e and f,cls | Debugger.test.e and f | test.e and f,global,delete | Debugger.test.e and f,cls,delete | Debugger.test.e and f,delete
        #
        # delete all:
        #    ,delete        # with leading comma!
        #
        # blanks in front of and behind each token are thrown away, blanks inside tokens are usually needed and, therefore, protected
        # e.g. "    test  . e and f    ,     global    " is identical with "test.e and f,global" but not with "test.eandf,global"
        # that is because variable names and dict keys should have leading or trailing blanks but can have blanks in between
        #
        # the "d.2" variables will be incremented, so if you are watching them or parent variables containing them you will get regular updates
        self.watches = {}
        global test
        test          = { "a" : 101, "b" : { "c" : 102 }, "d": [103, 104, 105, [106, 107], {"g" : [108, 109], "h": (110, 111, "class" )}], "e and f" : 112 }
        Debugger.test = { "a" : 201, "b" : { "c" : 202 }, "d": [203, 204, 205, [206, 207], {"g" : [208, 209], "h": (210, 211, "object")}], "e and f" : 212 }
        self.test     = { "a" : 301, "b" : { "c" : 302 }, "d": [303, 304, 305, [306, 307], {"g" : [308, 309], "h": (310, 311, "global")}], "e and f" : 312 }


    def setThreadDictionary(self, threadDictionary : dict):
        self.threadDictionary = threadDictionary


    def publishContent(self, debugVariable : dict, force : bool = False):
        publish = False
        if not debugVariable["error"]:
            try:
                if type(debugVariable["parent"][debugVariable["name"]]) == str or isinstance(debugVariable["parent"][debugVariable["name"]], numbers.Number):
                    currentContent = debugVariable["parent"][debugVariable["name"]]
                else:
                    currentContent = str(debugVariable["parent"][debugVariable["name"]])
                if force or (debugVariable["content"] != currentContent):
                    debugVariable["content"] = currentContent
                    publish = True
            except Exception as exception:
                pass
        else:
            publish = force

        if publish:
            self.mqttPublish(debugVariable["topic"], {debugVariable["homeAutomationName"] : debugVariable["content"]}, globalPublish = True, enableEcho = False)
            Supporter.debugPrint(f"DEBUG publish at topic {debugVariable['topic']}, content {debugVariable['homeAutomationName']}:{debugVariable['content']}")


    def debugMessageHandler(self, message : dict):
        '''
        Handles received debug messages. Debug messages can be sent via MQTT.
        Supported elements are:
            "variable" : "<object.variable>",          e.g. "variable" : "Logger.logCounter", where object is one of the objects given in json files and variable is any object variable
            "refreshTime" : <refresh time in seconds>, e.g "refreshTime" : 1, a refresh time of 0 means publish any change what can cause a lot of messages!
            "delete" : True/False,                     True means 
        '''
        def tokenizeVariable(variable : str, clsToken : bool = False, globalToken : bool = False, separator : str = None):
            '''
            class  variables get "CLS" in front of their names
            global variables get "GLOBAL" in front of their names
            '''
            if separator is None:
                separator = "."
            if clsToken:
                variable = f"CLS{separator}{variable}"
            elif globalToken:
                variable = f"GLOBAL{separator}{variable}"
            return variable

            
        def splitVariable(variable : str, clsToken : bool = False, globalToken : bool = False):
            '''
            Find real variable for given string
            '''
            variableArray = variable.split(".")
            variableArray = [entry.strip() for entry in variableArray]
            homeAssistantVariableName = "_".join(variableArray)
            homeAssistantVariableName = tokenizeVariable(homeAssistantVariableName, clsToken, globalToken, separator = "_")
            THREAD_ENTRY_POSITION = 1
            CLASS_POSITION        = 2

            if globalToken:
                debugVarRef = globals()                                                                                                 # path for "global" variables
            else:
                # class and object variables are accessible via threadDictionary in ProjectRunner 
                debugVarRef = globals()["Base"].__dict__["ProjectRunner"].__dict__["ProjectRunner"].__dict__["threadDictionary"]        # path for "self" variables
                variableArray.insert(THREAD_ENTRY_POSITION, "thread")

            variableName = ""
            error = None

            for index, entry in enumerate(variableArray):
                if clsToken and index == CLASS_POSITION:
                    # dereference __class__ in case of class variable
                    debugVarRef = debugVarRef.__class__

                if hasattr(debugVarRef, "__dict__"):
                    debugVarRef = debugVarRef.__dict__  # dereference __dict__ in any case if __dict__ exists

                if (type(debugVarRef) in [list,tuple]) and entry.isdigit() and (int(entry) < len(debugVarRef)):
                    if index == len(variableArray) - 1:
                        # debug variable finally found, setup watch point
                        variableName = int(entry)
                    else:
                        debugVarRef = debugVarRef[int(entry)]    # take next part of given debug variable (since watch needs a reference but following publish needs the content even after watch has been set up another dereferencing step is necessary)
                elif entry in debugVarRef:
                    if index == len(variableArray) - 1:
                        # debug variable finally found, setup watch point
                        variableName = entry
                    else:
                        debugVarRef = debugVarRef[entry]    # take next part of given debug variable (since watch needs a reference but following publish needs the content even after watch has been set up another dereferencing step is necessary)
                else:
                    # failed, given debug variable not found
                    debugVarRef = None
                    error = f"variable {variable} doesn't exist"
                    break

            # "debugVarRef" contains variable with name "variableName", "homeAssistantVariableName" is used to show information in home automation, error message is put into "error" if necessary 
            return debugVarRef, variableName, homeAssistantVariableName, error

        def discoverVariable(variable : str, clsToken : bool = False, globalToken : bool = False):
            '''
            Discovers variable at home automation
            '''
            tokenVariable = tokenizeVariable(variable, clsToken, globalToken)
            parentDict, variableName, homeAssistantVariableName, error = splitVariable(variable, clsToken, globalToken)
            topic = self.homeAutomation.mqttDiscoverySensor({homeAssistantVariableName : ""}, nameDict = {homeAssistantVariableName : f"{self.name} {tokenVariable}"}, subTopic = homeAssistantVariableName)
            self.watches[tokenVariable] = { "topic" : topic, "parent" : parentDict, "name" : variableName, "homeAutomationName" : homeAssistantVariableName, "debugName" : variable, "cls" : clsToken, "global" : globalToken }

            self.watches[tokenVariable]["error"] = error is not None
            if error is not None:
                self.watches[tokenVariable]["content"] = error

            self.publishContent(self.watches[tokenVariable], force = True)

        def undiscoverVariable(tokenVariable: str):
            '''
            Undiscovers tokenVariable from home automation
            '''
            self.mqttUnDiscovery(self.watches[tokenVariable]["homeAutomationName"])

        if "variable" in message:
            if matches:=re.match(r"^ *(?:(?P<variable>[^, ][^,]*?)(?: *, *(?:(?P<cls>cls)|(?P<global>global)))?(?: *, *(?P<delete>delete))?|(?: *, *(?P<deleteAll>delete))) *$", message["variable"], re.IGNORECASE):
                # delete all:
                # ===========
                #     matches.group("deleteAll") = delete
                #
                # delete one:
                # ===========
                #     matches.group("variable")  = variable
                #     matches.group("delete")    = delete
                #                                 
                #     matches.group("variable")  = variable
                #     matches.group("cls")       = cls
                #     matches.group("delete")    = delete
                #                                 
                #     matches.group("variable")  = variable
                #     matches.group("global")    = global
                #     matches.group("delete")    = delete
                #                                 
                # add one:                        
                # ========                        
                #     matches.group("variable")  = variable
                #                                 
                #     matches.group("variable")  = variable
                #     matches.group("cls")       = cls
                #                                 
                #     matches.group("variable")  = variable
                #     matches.group("global")    = global
                if matches.group("deleteAll") is not None:
                    # delete all
                    #    ,delete
                    for variable in self.watches:
                        undiscoverVariable(variable)
                    self.watches = {}
                elif matches.group("delete") is not None:
                    # delete one
                    #    variable,delete
                    #    variable,cls,delete
                    #    variable,global,delete
                    variable = matches.group("variable")
                    tokenVariable = tokenizeVariable(variable, clsToken = matches.group("cls") is not None, globalToken = matches.group("global") is not None)
                    if tokenVariable in self.watches:
                        undiscoverVariable(tokenVariable)
                    del self.watches[tokenVariable]
                elif matches.group("variable") is not None:
                    # add one
                    #    variable
                    #    variable,cls
                    #    variable,global
                    variable = matches.group("variable")
                    tokenVariable = tokenizeVariable(variable, clsToken = matches.group("cls") is not None, globalToken = matches.group("global") is not None)
                    if not tokenVariable in self.watches:
                        discoverVariable(variable, clsToken = matches.group("cls") is not None, globalToken = matches.group("global") is not None)
                    else:
                        pass    # nth. to do here, variable has already been added once before
                else:
                    # this "else" should not be reachable!
                    self.logger.debug(self, f"invalid match: [{str(message['variable'])}]")
            else:
                self.logger.debug(self, f"invalid variable content (expect \/([^,]+)?(,delete)?\/): [{str(message['variable'])}]")
        else:
            self.logger.debug(self, f"invalid message, key \"variable\" missed: [{str(message)}]")


    def threadInitMethod(self):
        '''
        Register needed topics here
        '''
        self.logger.info(self, "thread init (Debugger)")

        self.mqttSubscribeTopic(self.createInTopicFilter(self.objectTopic), globalSubscription = True)

        inTopic = self.createInTopic(self.objectTopic)
        self.outTopic = self.createOutTopic(self.objectTopic)
        self.homeAutomation.mqttDiscoveryText(textField = "Debugger Interface", commandTopic = inTopic, commandTemplate = '{ \\"variable\\" : \\"{{ value }}\\" }')
        self.homeAutomation.mqttDiscoveryText(textField = "Log Filter",         commandTopic = inTopic, commandTemplate = '{ \\"LogFilter\\" : \\"{{ value }}\\" }')
        self.homeAutomation.mqttDiscoveryText(textField = "Print Log Filter",   commandTopic = inTopic, commandTemplate = '{ \\"PrintLogFilter\\" : \\"{{ value }}\\" }')

        self.sensorValues = {"LogLevel" : Logger.get_logLevel().value, "PrintLogLevel" : Logger.get_printLogLevel().value}
        for sensor in sorted(self.sensorValues.keys()):
            self.homeAutomation.mqttDiscoveryInputNumberSlider(sensors = [sensor], maxValDict = {sensor : 5})
        self.sensorValues["LogFilter"] = Logger.get_logFilter()
        self.sensorValues["PrintLogFilter"] = Logger.get_printLogFilter()
        self.mqttPublish(self.outTopic, self.sensorValues, globalPublish = True, enableEcho = False)
        Supporter.debugPrint(f"published : {self.sensorValues}", color = "LIGHTRED", borderSize = 5)


    def threadMethod(self):
        if len(self.watches) and self.timer(name = "testTimer", timeout = 10):
            global test
            test["d"][2] += 1
            Debugger.test["d"][2] += 1
            self.test["d"][2] += 1

        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)      # read a message

#mosquitto_pub -t 'AccuTester/Debugger/in' -m '{"variable":"Logger.logCounter", "delete" : True,}' -h homeassistant -u pi -P raspberry
#mosquitto_pub -t 'homeassistant/text/AccuTester_DEBUG_VariableName/config' -m '{"name" : "hallo", "command_topic" : "AccuTester/DEBUG/in", "command_template":"{ \"variable\" : \"{{ value }}\" }"}' -h homeassistant -u pi -P raspberry

            if "content" in newMqttMessageDict:
                message = newMqttMessageDict["content"]
                if "LogLevel" in message:
                    Logger.set_logLevel(message['LogLevel'])
                    self.sensorValues['LogLevel'] = Logger.get_logLevel().value
                    self.mqttPublish(self.outTopic, self.sensorValues, globalPublish = True, enableEcho = False)
                elif "PrintLogLevel" in message:
                    Logger.set_printLogLevel(message['PrintLogLevel'])
                    self.sensorValues['PrintLogLevel'] = Logger.get_printLogLevel().value
                    self.mqttPublish(self.outTopic, self.sensorValues, globalPublish = True, enableEcho = False)
                elif "LogFilter" in message:
                    Logger.set_logFilter(message['LogFilter'])
                    self.sensorValues['LogFilter'] = Logger.get_logFilter()
                    self.mqttPublish(self.outTopic, self.sensorValues, globalPublish = True, enableEcho = False)
                elif "PrintLogFilter" in message:
                    Logger.set_printLogFilter(message['PrintLogFilter'])
                    self.sensorValues['PrintLogFilter'] = Logger.get_printLogFilter()
                    self.mqttPublish(self.outTopic, self.sensorValues, globalPublish = True, enableEcho = False)
                else:
                    if self.threadDictionary is not None:
                        try:
                            self.logger.debug(self, "received message :" + str(newMqttMessageDict))
                            self.debugMessageHandler(message)
                        except Exception as ex:
                            self.logger.debug(self, "invalid message" + str(newMqttMessageDict))

        # update all variables that have been changed since last time
        for variable in self.watches:
            self.publishContent(self.watches[variable])
