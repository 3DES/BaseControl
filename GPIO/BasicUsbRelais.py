import time
import sys
from Base.ThreadObject import ThreadObject
from queue import Queue
from Base.Supporter import Supporter
from collections import Counter


class BasicUsbRelais(ThreadObject):
    '''
    This class generates a {"cmd":"readRelayState"} and {"cmd":"readInputState"} msg all 60s and publishes it to the interface
    This class forwards all msg globally from interface

    Messages:
    {"cmd":"..."} will be forwarded to the interface
    {"cmd":"triggerWdRelay"} check if sender is the triggerThread and forward to the interface with "cmd":"triggerWd"
    {"gpio":{"relWr": "0", "relPvAus": "1", "relNetzAus": "0"}} will be mapped to {"setRelay":{"Relay0": "0", "Relay1": "1", "Relay5": "0", "Relay2": "1"}} and sent to the interface
    
    '''
    gpioCmd = "gpio"
    REL_OFF = "0"
    REL_ON = "1"

    # either the watchdog has to start its timer for its watchdog test or it has to wait until its index becomes next
    _WATCHDOG_NOT_INITIALIZED = -1
    _WATCHDOG_START_TIMER     = 0
    _WATCHDOG_MONITORING_OFF  = 1
    _WATCHDOG_EXECUTE_TEST    = 2
    _WATCHDOG_FINISH_TEST     = 3
    _WATCHDOG_MONITORING_ON   = 4
    _WATCHDOG_NEXT_ONE        = 5
    _WATCHDOG_WAIT_FOR_INDEX  = 6
    nextWatchDogAction = _WATCHDOG_NOT_INITIALIZED


    _TIME_BETWEEN_TESTS = 4*24*60*60    # Watchdog Test every max 100h, we do it all 4d = 4*24*60*60
    _WAIT_TIME_FOR_FIRST_TEST = 150     # wait with the first test until this time is gone, if the DCbox starts auomatically then we need a quiet long time here
    _MIN_TIME_BETWEEN_TESTS = 60        # parametrized time should not be lower that this amount of seconds
    _TIME_BETWEEN_CANDIDATES = 10       # when it's time for another test, a candidate waits 30 seconds until it starts its test when it got the test tocken from its predecessor
    _TIME_FOR_TEST = 20                 # after 20 seconds watchdog should have finished its test


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["triggerThread"], optional = True, default = "noTriggerThreadDefined")
        self.tagsIncluded(["relMapping"], optional = True, default = {})
        self.tagsIncluded(["inputMapping"], optional = True, default = {})
        self.tagsIncluded(["gpioHandler"], optional = True, default = [])
        self.tagsIncluded(["noInitialTest"], optional = True, default = False)                          # if False the first test will be executed earlier than given in "timeBetweenTests", otherwise the first test will be executed after "timeBetweenTests" seconds
        self.tagsIncluded(["timeBetweenTests"], optional = True, default = self._TIME_BETWEEN_TESTS)    # seconds between test execution but also the time it takes until the first test is executed
        if self.configuration["timeBetweenTests"] > self._TIME_BETWEEN_TESTS:                           # there is a maximum allowed time between tests
            self.logger.warning(self, f"timeBetweenTests parameter is too large and will be reduced to {self._TIME_BETWEEN_TESTS}")
            self.configuration["timeBetweenTests"] = self._TIME_BETWEEN_TESTS
        elif self.configuration["timeBetweenTests"] < self._MIN_TIME_BETWEEN_TESTS:                     # there is a minimum allowed time between tests
            self.logger.warning(self, f"timeBetweenTests parameter is too short and will be set to {self._MIN_TIME_BETWEEN_TESTS}")
            self.configuration["timeBetweenTests"] = self._MIN_TIME_BETWEEN_TESTS
        self.tagsIncluded(["publish"], optional = True, default = False, valueType = type(True))
        self.triggerActive = True
        self.executedTestsCounter = 0

        # to synchronize hardware watchdogs others have to be given, otherwise the test executed every x hours will fail!
        # all watchdogs will subscribe to all others' outtopics and only the master handles the timer
        # when the master sends out that it has done its test, the next one in the row can execute its test, and so on...
        watchDogList = [ self.name ]            # add current watchdog to the watchdog list but make all entries unique again later on to ensure that it doesn't matter if the configurator adds all watchdogs to the watchdog list or not  
        if self.tagsIncluded(["watchdogRelays"], optional = True, default = []):
            if type(self.configuration["watchdogRelays"]) == list:
                watchDogList += self.configuration["watchdogRelays"]
            else:
                watchDogList.append(self.configuration["watchdogRelays"])
        watchDogList = list(set(watchDogList))  # make all entries unique!
        watchDogList.sort()                     # sort the list to get alphanumeric order, what will be necessary later on to decide when current watchdog can execute its test

        # decide who's the master watchdog, that initiates the test chain
        MASTER_WATCHDOG_INDEX = 0                                                       # first one in the list will become the master watchdog
        self.masterWatchDog = (watchDogList[MASTER_WATCHDOG_INDEX] == self.name)        # True/False
        self.watchDogIndex = -1                                                         # has to be set to correct value later on!

        # check who's the master watchdog and do necessary initial settings
        self.watchDogIndex = watchDogList.index(self.name)                      # get index of current watchdog inside the sorted watchdog list
        self.masterWatchDog = (self.watchDogIndex == MASTER_WATCHDOG_INDEX)     # is current watchdog the master one?
        if self.masterWatchDog:
            self.watchDogPredecessorIndex = len(watchDogList) - 1               # current watchdog is next in chain if last publishing watchdog was predecessor watchdog (predecessor of master is last watchdog in watchdog chain)
            self.nextWatchDogAction = self._WATCHDOG_START_TIMER                # master watchdog has to start its timer first
            self.watchDogTimeout = self.configuration["timeBetweenTests"]
        else:
            self.watchDogPredecessorIndex = self.watchDogIndex - 1              # current watchdog is next in chain if last publishing watchdog was predecessor watchdog
            self.nextWatchDogAction = self._WATCHDOG_WAIT_FOR_INDEX             # non-master watchdog has to wait until it's its turn
            self.watchDogTimeout = self._TIME_BETWEEN_CANDIDATES                # predecessor watchdog gets 10 seconds for its test

        # subscribe to predecessor        
        self.mqttWdTestQueue = Queue(self.QUEUE_SIZE)                           # for easier handling subscribe watchdog test monitoring with separate queue
        subTopic = "watchDogTest"
        self.watchDogTestTopic = self.createOutTopic(self.createProjectTopic(self.name), subTopic = subTopic)
        predecessorOutTopic = self.createOutTopic(self.createProjectTopic(watchDogList[self.watchDogPredecessorIndex]), subTopic = subTopic)
        self.mqttSubscribeTopic(predecessorOutTopic, globalSubscription = False, queue = self.mqttWdTestQueue)
        
        # if publish has been given accept relay changes from outside!
        if self.configuration["publish"]:
            self.mqttSubscribeTopic(self.createInTopicFilter(self.objectTopic), globalSubscription = True)

        self.knownRelayStates = {}      # all relays for which a set or clear command has been received will be stored here for publishing their states to home automation
        self.knownInputStates = {}      # all relays for which a set or clear command has been received will be stored here for publishing their states to home automation


    def handleWatchdogTest(self):
        '''
        Watchdog test has to ensure that during the test no triggering will be done since it will fail!
        Futhermore, there can be several watchdogs and all of them have to execute their tests one after another and not together to prevent any race conditions.
        '''
        def publishStateSwitch(message : str):
            # inform next watchdog in watchdog chain
            self.mqttPublish(self.watchDogTestTopic,
                {
                    "watchDogTestIndex":self.watchDogIndex, 
                    "watchDogTestRequest":message
                },
                globalPublish = False,
                enableEcho = True)      # if there is only one watchdog in the chain it must be able to send the message out to itself!

        # handle watchdog test
        if self.nextWatchDogAction == self._WATCHDOG_START_TIMER:
            testTimeout = self.watchDogTimeout

            # in case of very first test and if "noInitialTest" has not been set, reduce time for first test to minimum time
            if self.masterWatchDog:
                if self.executedTestsCounter == 0:
                    if not self.configuration["noInitialTest"]:
                        testTimeout = self._WAIT_TIME_FOR_FIRST_TEST

            if self.timer(name = "timerTestWd", timeout = testTimeout, autoReset = True):
                self.executedTestsCounter += 1
                self.triggerActive = False                                                                                                      # de-activating triggering for current watchdog since it's tested now
                publishStateSwitch("TRIGGERING_DISABLED")                                                                                       # inform next watchdog in watchdog chain
                self.nextWatchDogAction = self._WATCHDOG_MONITORING_OFF                                                                         # now wait until whole watchdog chain has been handled
                self.timer(name = "timerTestWd", remove = True)                                                                                 # one shot timer no longer needed
        elif self.nextWatchDogAction == self._WATCHDOG_EXECUTE_TEST:
            if not self.toSimulate():
                self.mqttPublish(self.interfaceInTopics[0], {"cmd":"testWdRelay"}, globalPublish = False, enableEcho = False)                   # command watchdog test
            self.nextWatchDogAction = self._WATCHDOG_FINISH_TEST
        elif self.nextWatchDogAction == self._WATCHDOG_FINISH_TEST:
            # xxxxxxxxxxxxxx @TODO hier besser auf Antwort von Relay warten!!!
            if self.timer(name = "timerTestEndWd", timeout = self._TIME_FOR_TEST, oneShot = True):                                              # give test some seconds time to finish
                publishStateSwitch("TRIGGERING_ENABLED")                                                                                        # inform next watchdog in watchdog chain
                self.nextWatchDogAction = self._WATCHDOG_MONITORING_ON
                self.timer(name = "timerTestEndWd", remove = True)                                                                              # one shot timer no longer needed
        elif self.nextWatchDogAction == self._WATCHDOG_NEXT_ONE:
            publishStateSwitch("NEXT_ONE_PLEASE")                                                                                               # inform next watchdog in watchdog chain
            self.nextWatchDogAction = self._WATCHDOG_WAIT_FOR_INDEX
            self.triggerActive = True     
        else:
            while not self.mqttWdTestQueue.empty():
                predecessorMessageDict = self.readMqttQueue(self.mqttWdTestQueue, error = False)
                messageContent = predecessorMessageDict["content"]
                if "watchDogTestIndex" in messageContent and "watchDogTestRequest" in messageContent:
                    if messageContent["watchDogTestIndex"] == self.watchDogPredecessorIndex:
                        if messageContent["watchDogTestRequest"] == "TRIGGERING_DISABLED":
                            self.triggerActive = False                                                                                          # de-activate triggering for other watchdogs when one watchdog is currently testing
                            if self.nextWatchDogAction == self._WATCHDOG_MONITORING_OFF:
                                self.nextWatchDogAction = self._WATCHDOG_EXECUTE_TEST                                                           # actively testing watchdog will proceed
                            else:
                                publishStateSwitch("TRIGGERING_DISABLED")                                                                       # all others will just inform the next one in the chain
                        elif messageContent["watchDogTestRequest"] == "TRIGGERING_ENABLED":
                            self.triggerActive = True                                                                                           # re-activate triggering for other watchdogs since the testing one has finished its test
                            if self.nextWatchDogAction == self._WATCHDOG_MONITORING_ON:
                                self.nextWatchDogAction = self._WATCHDOG_NEXT_ONE                                                               # active testing watchdog will proceed
                            else:
                                publishStateSwitch("TRIGGERING_ENABLED")                                                                        # all others will just inform the next one in the chain
                        elif messageContent["watchDogTestRequest"] == "NEXT_ONE_PLEASE":
                            # ok, token received so current watchdog is next tester
                            self.nextWatchDogAction = self._WATCHDOG_START_TIMER
                    else:
                        raise Exception(f"{self.watchDogIndex} received watch dog test message from wrong predecessor, expected {self.watchDogPredecessorIndex} but got {messageContent['watchDogTestIndex']}")
                else:
                    raise Exception(f"{self.watchDogIndex} received watch dog test message without valid key: {predecessorMessageDict}")


    def publishIOs(self):
        publishDict = {}
        publishDict["inputs"] = self.knownInputStates
        publishDict["outputs"] = self.knownRelayStates
        self.logger.debug(self, f"update IO data: {publishDict}")
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), publishDict, globalPublish = False, enableEcho = False)
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), publishDict, globalPublish = True, enableEcho = False)


    def threadInitMethod(self):
        self.mqttPublish(self.interfaceInTopics[0], "readRelayState", globalPublish = False, enableEcho = False)
        self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(self.configuration["triggerThread"]), self.MQTT_SUBTOPIC.TRIGGER_WATCHDOG), globalSubscription = False)
        for gpioHandler in self.configuration["gpioHandler"]:
            self.mqttSubscribeTopic(self.createOutTopic(self.createProjectTopic(gpioHandler)), globalSubscription = False)

        # publish inputs
        inputNames = []
        if "inputs" in self.configuration:
            inputNames = [f"Input{i}" for i in range(self.configuration["inputs"])]
        if "inputMapping" in self.configuration:
            for inputName in self.configuration["inputMapping"].keys():
                if not inputName in inputNames:
                    inputNames.append(inputName)
        for inputName in inputNames:
            niceName = f"{self.name} {inputName}"
            sensorName = inputName
            if inputName in self.configuration["inputMapping"]:
                niceName += f" ({self.configuration['inputMapping'][inputName]})"
                sensorName = self.configuration['inputMapping'][inputName]

            preparedMsg = self.homeAutomation.getDiscoverySensorCmd(deviceName = "", sensorName = sensorName, niceName = niceName, unit = "none", topic = self.createOutTopic(self.getObjectTopic()), subStructure = "inputs", payloadOn = "1", payloadOff = "0")
            sensorTopic = self.homeAutomation.getDiscoverySensorTopic(deviceName = self.name, sensorName = inputName, readOnly = True)
            self.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)
            self.logger.debug(self, f"discover sensor at topic {sensorTopic}, message {preparedMsg}")

        # publish outputs (= relays) only if publish parameter has been set to True 
        outputNames = []
        reverseRelayDict = {}
        if "outputs" in self.configuration:
            outputNames = [f"Relay{i}" for i in range(self.configuration["outputs"])]
            reverseRelayDict = {f"Relay{i}" : f"Relay{i}" for i in range(self.configuration["outputs"])}
        if "relMapping" in self.configuration:
            # relMapping can contain a relay list for some relays!
            for relay in self.configuration["relMapping"].keys():
                if type(self.configuration["relMapping"][relay]) == list:
                    outputList = self.configuration["relMapping"][relay]        # take the defined list
                else:
                    outputList = [self.configuration["relMapping"][relay]]      # create a list with one element

                for outputName in outputList:
                    if not outputName in outputNames:
                        outputNames.append(outputName)
                    reverseRelayDict[outputName] = relay        # overwrite named relays, all others will get RelayN as name

        for outputName in outputNames:
            niceName = f"{self.name} {outputName}"
            sensorName = outputName
            if outputName != reverseRelayDict[outputName]:
                niceName += f" ({reverseRelayDict[outputName]})"

            preparedMsg = self.homeAutomation.getDiscoverySensorCmd(deviceName = "", sensorName = outputName, niceName = niceName, unit = "none", topic = self.createOutTopic(self.getObjectTopic()), subStructure = "outputs", payloadOn = "1", payloadOff = "0")
            sensorTopic = self.homeAutomation.getDiscoverySensorTopic(deviceName = self.name, sensorName = outputName, readOnly = True)
            self.mqttPublish(sensorTopic, preparedMsg, globalPublish = True, enableEcho = False)
            self.logger.debug(self, f"discover sensor at topic {sensorTopic}, message {preparedMsg}")

            switchTopic = self.homeAutomation.getDiscoverySwitchTopic(self.name, outputName)
            preparedMsg = self.homeAutomation.getDiscoverySwitchCmd(deviceName = self.name, sensorName = sensorName, niceName = niceName, subStructure = "outputs", payloadOn = f'{{ "inputs" : {{"{sensorName}" : "1"}} }}', payloadOff = f'{{ "inputs" : {{"{sensorName}" : "0"}} }}', stateOn = '1', stateOff = '0')
            if self.configuration["publish"]:
                self.mqttPublish(switchTopic, preparedMsg, globalPublish = True, enableEcho = False)
                self.logger.debug(self, f"discover switch at topic {switchTopic}, message {preparedMsg}")
            else:
                self.mqttPublish(switchTopic, "", globalPublish = True, enableEcho = False)
                self.logger.debug(self, f"un-discover switch at topic {switchTopic}")


    def threadSimmulationSupport(self):
        '''
        Necessary since this thread supports SIMULATE flag
        '''
        pass    # nth. else to do here


    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            # check if we got a msg from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if "inputs" in newMqttMessageDict["content"]:
                    inputs = newMqttMessageDict["content"]["inputs"]
                    namedInputs = {}
                    for inputName in inputs.keys():
                        if inputName in self.configuration["inputMapping"]:
                            # rename key since input has a defined name (i.e. Input0 is e.g. watchDogState)
                            namedInputs[self.configuration["inputMapping"][inputName]] = inputs[inputName]
                        else:
                            # take default input name since input has no defined name (i.e. Input1 is Input1)
                            namedInputs[inputName] = inputs[inputName]
                    self.knownInputStates.update(namedInputs)       # set or update new input states
                    self.publishIOs()
                elif not "triggerWd" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"], globalPublish = True, enableEcho = False)
            else:
                if "cmd" in newMqttMessageDict["content"]:
                    # We only send triggerWd if the triggerThread triggers the wd
                    if newMqttMessageDict["content"]["cmd"] == "triggerWdRelay" and self.configuration["triggerThread"] in newMqttMessageDict["topic"]:
                        # ignore triggering during watchdog selftest
                        if self.triggerActive:
                            # This is a special msg. Watchdog will be only triggered if the sender thread is accepted. We convert the Msg to prevent that a thread can trigger interface directly.
                            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"triggerWd"}, globalPublish = False, enableEcho = False)
                    else:
                        self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                else:
                    # We only accept gpio commands from gpioHandlers
                    relaysFound = False
                    validHandler = False
                    for threadnames in self.configuration["gpioHandler"]:
                        if f"/{threadnames}/" in newMqttMessageDict["topic"]:
                            validHandler = True
                            if self.gpioCmd in newMqttMessageDict["content"]:
                                # handle all received relay states
                                tempRelais = {}
                                for key in list(self.configuration["relMapping"].keys()):
                                    if key in newMqttMessageDict["content"][self.gpioCmd]:
                                        relaysFound = True
                                        if type(self.configuration["relMapping"][key]) == list:
                                            for relais in self.configuration["relMapping"][key]:
                                                tempRelais.update({relais : newMqttMessageDict["content"][self.gpioCmd][key]})
                                        else:
                                            tempRelais.update({self.configuration["relMapping"][key] : newMqttMessageDict["content"][self.gpioCmd][key]})
                                        if not (newMqttMessageDict["content"][self.gpioCmd][key] in [self.REL_OFF, self.REL_ON]):
                                            raise Exception(f'{self.name} got a wrong value for relay state. Check your code. Relayname was: {key}, value: {newMqttMessageDict["content"][self.gpioCmd][key]}')

                                # since gpioHandlers usually publish more than just our relays here publish relay states only if there were some in the received message
                                if relaysFound:
                                    self.mqttPublish(self.interfaceInTopics[0], {"setRelay" : tempRelais}, globalPublish = False, enableEcho = False)
                                    self.knownRelayStates.update(tempRelais)
                                    self.publishIOs()
                                    break
                    if not validHandler:
                        if self.configuration["publish"] and (newMqttMessageDict["topic"] == self.createInTopic(self.objectTopic)) and ("content" in newMqttMessageDict) and ("inputs" in newMqttMessageDict["content"]):
                            # because of publish we accept relay changes on our input topic, too! In that case the names from relMapping are not used since they are only known by our default handlers, so accept Relay0..n instead
                            self.mqttPublish(self.interfaceInTopics[0], {"setRelay" : newMqttMessageDict["content"]["inputs"]}, globalPublish = False, enableEcho = False)
                            self.knownRelayStates.update(newMqttMessageDict["content"]["inputs"])
                            self.publishIOs()
                            self.logger.debug(self, f"got message from not registered handler what is OK since 'publish' configuration has been set to True: {newMqttMessageDict}")
                        else:
                            raise Exception(f'{self.name} got message from unknown handler: {newMqttMessageDict}\nvalid handlers: {self.configuration["gpioHandler"]}')

        if self.timer(name = "timerWdStateTest", timeout = 90) and self.triggerActive:
            self.mqttPublish(self.interfaceInTopics[0], {"cmd" : "checkWdState"}, globalPublish = False, enableEcho = False)

        if self.timer(name = "timerStateReq", timeout = 60):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd" : "readRelayState"}, globalPublish = False, enableEcho = False)
            self.mqttPublish(self.interfaceInTopics[0], {"cmd" : "readInputState"}, globalPublish = False, enableEcho = False)

        self.handleWatchdogTest()


    def threadBreak(self):
        time.sleep(0.2)
