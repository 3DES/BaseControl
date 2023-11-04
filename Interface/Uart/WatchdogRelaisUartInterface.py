import time

from Interface.Uart.BasicUartInterface import BasicUartInterface
from Base.Supporter import Supporter
import Base.Crc
import os
import subprocess
import re
import colorama



class WatchdogRelaisUartInterface(BasicUartInterface):
    '''
    This class is a Interface for a watchdog relay.
    This is a Arduino Nano with special Relays which have to be pulsed.
    If not the relay switch off.
    If Nanos firmware is not triggered via uart it will switch also off.
    https://github.com/3DES/WatchdogBoard
    
    This class will forward a watchdog msg (normally from BaseControlls Watchdog) with crc to the usb Relay.
    This class checks the firmware of usb relay and update if its neccessary.
    This class polls inputs an publish if ther is a new value

    Messages:
    {"cmd":"readInputState"} publishes the localInputState
    {"cmd":"triggerWdRelay"} trigger the external wd relay
    {"cmd":"clearWdRelay"} resets the external wd relay
    {"cmd":"testWdRelay"} send the Test Command to the wd relay
    {"setRelay":{"Relay0": "0", "Relay1": "1", "Relay5": "0", "Relay2": "1"}} set the Relay state


        > 0;V;5971;\n                       # get version
        < 0;V;1.0_4xUNPULSED;63918;\n       # returns version information
        > 1;W;1;43612;\n                    # trigger watchdog
        < 1;W;0;1;17361;\n                  # OK, watchdog state switched from 0 to 1
        > 2;W;0;1;333;\n                    # simulate communication error
        < 2;E;2;[2;W;0;1;333;];44598;\n     # OK, error responded
        > 2;W;1;42529;\n                    # re-trigger watchdog
        < 2;W;1;1;54714;\n                  # OK, watchdog state stayed at 1
        > 3;S;0;1;22546;\n                  # switch output 0 to ON
        < 3;S;0;0;1;19258;\n                # OK, output 0 was 0 and changed to 1
        > 4;S;1;1;55463;\n                  # switch output 1 to ON
        < 4;S;1;0;1;35812;\n                # OK, output 1 was 0 and changed to 1
        > 5;W;1;47856;\n                    # re-trigger watchdog
        < 5;W;1;1;18868;\n                  # OK, watchdog state stayed at 1
        > 6;R;0;49410;\n                    # read input 0
        < 6;R;0;0;53888;\n                  # OK, input 0 is 0
        -- switch ON input 0 now --
        > 7;R;0;50473;\n                    # read input 0
        < 7;R;0;1;19175;\n                  # OK, input 0 is 1 now
        > 8;S;1;0;64029;\n                  # switch output 1 to OFF again
        < 8;S;1;1;0;22322;\n                # OK, output 1 was 1 and changed to 0
        
        
        todo: aktuell bekomme ich nicht mit mit wenn der WD abfällt wenn ihn keiner triggert.
        todo: wd trigger cmd {"cmd":"triggerWdRelay"} in den watchdog.py einbauen und an alle wd schicken (Liste über init.json übergeben)
        todo: getFirmwarePath() und getAvrDudePath() an linux final anpassen und ggf zwisch windows und linux unterscheiden

        todo: neue Firmware einchecken und getAndLogDiagnosis() anpassen und testen

    '''
    magicWord = "4D4853574D485357"          # MHSWMHSW
    maxUpdateTries = 4
    bootTime = 2.5


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.separator = ";"
        self.comandEnd = ";\n"
        self.frameCounter = 0
        self.relayMapping = {"Relay0": "0", "Relay1": "1", "Relay2": "2", "Relay3": "3", "Relay4": "4", "Relay5": "5", "Relay6": "6"}
        self.inputMapping = {"Input0": "0", "Input1": "1", "Input2": "2", "Input3": "3"}
        self.localInputState = {"Input0": "None", "Input1": "None", "Input2": "None", "Input3": "None"}

        self.tagsIncluded(["firmware"])
        self.tagsIncluded(["avrdudePath"], optional = True, default = "avrdude")
        self.firstLoop = True
        self.getDiagnosis = False
        self.wdEverTriggered = False


    # some helper funktions
    def getKeyFromVal(self, dic, val):
        for key in list(dic):
            if val == dic[key]:
                return key

    def getCRC(self, cmd):
        crc = Base.Crc.Crc.crc16EasyMeter(Supporter.encode(cmd))
        return str(crc)

    def getCommand(self, cmdStr):
        cmdStr = f"{self.frameCounter}{self.separator}" + cmdStr
        cmdStr += self.separator
        crc = self.getCRC(cmdStr)
        cmd = cmdStr + crc
        cmd = cmd + self.comandEnd
        cmd = Supporter.encode(cmd)
        return cmd

    def processMsg(self, msg):
        if not len(msg):
            self.logger.error(self, f"Empty msg to process!")
            return {"Error":"noMsg"}

        msg = msg.split(";")

        if len(msg) < 3:
            self.logger.error(self, f"No valid msg to process! Msg: {msg}")
            return {"Error":"noMsg"}

        framenumber = 0
        cmd         = 1
        port        = 2
        errorType   = 2
        firmwareName= 2
        testResult  = 2
        value       = 3
        newValue    = 4
        # now the ErrorCodings from Relais
        eERROR_NO_ERROR = "0"
        eERROR_UNKNOWN_COMMAND = "1"
        eERROR_UNKNOWN_STATE = "2"
        eERROR_INVALID_FRAME_NUMBER = "3"
        eERROR_UNEXPECTED_FRAME_NUMBER = "4"
        eERROR_INVALID_VALUE = "5"
        eERROR_INVALID_INDEX = "6"
        eERROR_INVALID_CRC = "7"
        eERROR_OVERFLOW = "8"
        eERROR_INVALID_STARTUP = "9"
        del msg[-1]                                         # delete /r/n
        msgCrc = msg[len(msg)-1]                            # ectract crc
        del msg[-1]                                         # delete crc
        crc = self.getCRC(";".join(msg)+self.separator)     # calculate crc
        if crc != msgCrc:
            self.logger.error(self, f"Wrong CRC received. Ours: {crc}, Wd: {msgCrc}")
            return {"Error":"crc"}
        if not int(msg[framenumber]) == self.frameCounter:
            self.logger.error(self, f"Framenumber not same. Ours: {self.frameCounter} Wd: {msg[framenumber]}")
            return {"Error":"framenumber", "requiredFramenumber":int(msg[framenumber])}
        if msg[cmd] == "S":
            return {self.getKeyFromVal(self.relayMapping, msg[port]):msg[newValue]}
        elif msg[cmd] == "R":
            return {self.getKeyFromVal(self.inputMapping, msg[port]):msg[value]}
        elif msg[cmd] == "V":
            return msg[firmwareName]
        elif msg[cmd] == "W":
            return msg[value]
        elif msg[cmd] == "T":
            return msg[testResult]
        elif msg[cmd] == "D":
            return ";".join(msg)
        elif msg[cmd] == "E":
            self.logger.error(self, f"Relay respondet an error: {msg}")
            if msg[errorType] == eERROR_INVALID_CRC:
                # We actual dont make a difference between internal crc error or relais crc error. Just resend msg.
                return {"Error":"crc"}
            elif msg[errorType] == eERROR_INVALID_STARTUP:
                return {"Error":"invalidStartup"}
            else:
                return {"Error":"E"}

    def processSerialCmd(self, cmd):
        maxTries = 10
        for tries in range(maxTries):
            if tries > 3:
                self.logger.error(self, f"We try to reinit serial because there are many errors.")
                self.reInitSerial()
            self.serialReset_input_buffer()
            wdCommand = self.getCommand(cmd)
            self.serialWrite(wdCommand)
            response = self.serialReadLine()
            #Supporter.debugPrint([f"{self.name}:", f"write {wdCommand}", f"read  {response}"], color = "GREEN")
            procMsg = self.processMsg(Supporter.decode(response))
            if not "Error" in procMsg:
                self.frameCounter +=1
                if self.frameCounter > 0xFFFF:
                    self.frameCounter = 0
                return procMsg
            else:
                delayNextRead = True
                if procMsg["Error"] == "noMsg" and cmd == "V":
                    # If we got no msg on version request we suggest that there is a new Arduino plugged in.
                    return "newArduino"
                if procMsg["Error"] == "framenumber":
                    self.frameCounter = procMsg["requiredFramenumber"]
                    self.logger.error(self, f"We try to set right framenumber {self.frameCounter}, and resend msg. Tries: {tries}")
                    delayNextRead = False
                    # todo wenn framenumber 0 dann sollten wir evtl einen eventuellen Reset des wdRel behandeln
                elif procMsg["Error"] == "invalidStartup":
                    raise Exception("Got an invalid startup error from watchdog!")
                elif procMsg["Error"] == "crc":
                    self.logger.error(self, f"Crc Error! We try to resend msg. Retries: {tries}")
                    delayNextRead = False
                if not self.getDiagnosis:
                    # prevent recursion if we get an error while getAndLogDiagnosis()
                    self.logger.error(self, f"We sent CMD: {wdCommand}, real framenumber would have been {self.frameCounter}")
                    self.getAndLogDiagnosis()
                if delayNextRead:
                    time.sleep(2)
        raise Exception("After few communication errors we stop Basecontrol")

    def sendCommand(self, command):
        cmdstr = f"{command}"
        return self.processSerialCmd(cmdstr)

    def sendRequest(self, command, port):
        cmdstr = f"{command}{self.separator}{port}"
        return self.processSerialCmd(cmdstr)

    def sendValue(self, command, port, value):
        cmdstr = f"{command}{self.separator}{port}{self.separator}{value}"
        return self.processSerialCmd(cmdstr)

    def publishInputState(self):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"inputs":self.localInputState}, globalPublish = False, enableEcho = False)

    def getHwVersion(self):
        version = self.sendCommand("V")
        return version

    def getFirmwarePath(self):
        return os.path.join(os.getcwd(), "Firmware", self.configuration["firmware"])

    def runAvrDude(self):
        return subprocess.run([self.configuration["avrdudePath"], '-c', 'arduino', '-p', 'm328p', '-P', self.configuration["interface"], '-b', '115200', '-U', fr'flash:w:{self.getFirmwarePath()}:a'], capture_output=True)

    def getOurVersion(self):
        # Coding in .hex file MHSWMHSW*MHSWMHSW, where * is name of the firmware
        f = open(self.getFirmwarePath(), "r")
        rawData = ""
        for line in f:
            rawData += line[9:-3]
        ourFw = re.findall(f'{self.magicWord}(.*){self.magicWord}', rawData)
        if not len(ourFw):
            return ""
        else:
            ourFw = ourFw[0]
            # delete 00
            while ourFw[-2:] == '00':
                ourFw = ourFw[:-2]
            return bytes.fromhex(ourFw).decode('utf-8')

    def updateArduio(self):
        try:
            self.clearWdRelay()
        except:
            self.logger.error(self, f"Arduino update. clearWdRelay() not possible! Try to update now.")

        self.serialClose()
        tries = 0
        while self.maxUpdateTries > tries:
            tries += 1
            avrDudeRet = self.runAvrDude()
            if avrDudeRet.returncode:
                self.logger.error(self, f"Arduino update Error! RetVal: {avrDudeRet.stdout}, {avrDudeRet.stderr}")
                self.logger.error(self, f"Arduino update. Wait 35s and Retry.")
                time.sleep(35)    # Wait because the reset of arduino migth be locked. It will be unlocked 30s after clearWdRelay.
            else:
                self.logger.info(self, f"Arduino update Ok")
                self.reInitSerial()
                self.frameCounter = 0
                time.sleep(self.bootTime)
                self.getAndLogDiagnosis()
                break

    def getVersionAndUpdate(self):
        hwFw = self.getHwVersion()
        ourFw = self.getOurVersion()
        if hwFw != ourFw:
            self.logger.info(self, f"Watchdog firmware differs from ours. We will update. Ours: --{ourFw}-- Wd: --{hwFw}--")
            self.updateArduio()

            hwFw = self.getHwVersion()
            if hwFw != ourFw:
                raise Exception(f"Wrong firmware after update Ours: --{ourFw}-- Wd: --{hwFw}--. Required Bootloader: ../BaseControl/Firmware/optiboot_atmega328.hex. Please check.")
        else:
            self.logger.info(self, f"Watchdog firmware is up to date. Ours: --{ourFw}-- Wd: --{hwFw}--")

    def getAndLogDiagnosis(self):
        '''
        Diagnosis command contains diagnosis, errors and executed tests, e.g.
                                    0;D;1;0;0
                                        | | |
              diagnosis info  ----------  | | 
              error number    ------------  |
              # executed tests  ------------
              
              currently used values (version "1.5_4xUNPULSED"):
                eERROR_INITIAL_SELF_TEST_ERROR           = 0x0001,   // error number in case of self test error during self test initial phase
                eERROR_REPEATED_SELF_TEST_ON_ERROR       = 0x0002,   // error number in case of self test error while self test has been repeated
                eERROR_REPEATED_SELF_TEST_OFF_ERROR      = 0x0003,   // error number in case of self test error while self test has been repeated
                eERROR_REPEATED_SELF_TEST_REQUEST_MISSED = 0x0004,   // error number in case of self test has not been requested early enough
                eERROR_WATCHDOG_NOT_TRIGGERED            = 0x1000,   // watchdog was already running but it was not triggered anymore
                eERROR_WATCHDOG_CLEARED                  = 0x1001,   // watchdog was already running and has been cleared via command
                eERROR_WATCHDOG_STOPPED_UNEXPECTEDLY     = 0x1002,   // watchdog was already running but now it has been stopped but is not in ERROR state

                eDIAGNOSIS_STARTUP = 1 << 0,

                eEXECUTED_TEST_SELF_TEST = 1 << 0,         // lowest bit is self test indicator
        '''
        self.getDiagnosis = True        # To Prevent Recursion during handling error and get a error during getAndLogDiagnosis()
        self.logger.error(self,f'Watchdog Diagnosis: {self.sendCommand("D")}')
        self.getDiagnosis = False



    # now the funktions to manage relay
    def testWdRelay(self):
        result = self.sendCommand("T")
        if not result == "1":
            self.logger.error(self,f'Test command rejected! Watchdog Diagnosis: {self.sendCommand("D")}')
        return result

    def triggerWdRelay(self):
        self.wdEverTriggered = True
        retval = self.sendRequest("W", "1")
        if not retval == "1":
            self.getAndLogDiagnosis()
            raise Exception("Watchdog was not running after trigger, PowerPlant will be stopped! Watchdog seems to be in any error state and blocks reset pin for 1 minute, e.g. because PowerPlant has been stopped and Watchdog hasn't been retriggered, or self test failed, or there is any other reason why the watchdog cannot be reset.")
        return retval

    def clearWdRelay(self):
        self.sendRequest("W", "0")

    def readInputState(self):
        inputs = {}
        for pin in list(self.inputMapping):
            inputs.update(self.sendRequest("R", self.inputMapping[pin]))
        return inputs

    def setRelayStates(self, relayState):
        for relay in list(relayState):
            self.sendValue("S", self.relayMapping[relay], relayState[relay])
            if not self.wdEverTriggered and relayState[relay] == "1":
                # If the watchdog is 0 we cannot set any relais. A clean timing is: trigger wd first and then set relais. This is not easy if this is done by different threads.
                self.logger.error(self,f'Setting of relay -{relay}- to 1 maybe has no effect, wd was never triggered. Please see -triggerThread- in project.json. Or check timing!')

    def threadMethod(self):
        if self.firstLoop:
            time.sleep(self.bootTime)
            self.firstLoop = False
            self.getVersionAndUpdate()
            self.setRelayStates({"Relay0": "0", "Relay1": "0", "Relay2": "0", "Relay3": "0", "Relay4": "0", "Relay5": "0", "Relay6": "0"})

        # Polling inputs in each loop and publish if there is a new value
        tempInputState = self.readInputState()
        if self.localInputState != tempInputState:
            self.localInputState = tempInputState
            self.publishInputState()

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "cmd" in newMqttMessageDict["content"]:
                if "readInputState" == newMqttMessageDict["content"]["cmd"]:
                    self.publishInputState()
                elif "triggerWd" == newMqttMessageDict["content"]["cmd"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"triggerWd":self.triggerWdRelay()}, globalPublish = False, enableEcho = False)
                elif "testWdRelay" == newMqttMessageDict["content"]["cmd"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"testWdRelay":self.testWdRelay()}, globalPublish = False, enableEcho = False)
                elif "clearWdRelay" == newMqttMessageDict["content"]["cmd"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"clearWdRelay":self.clearWdRelay()}, globalPublish = False, enableEcho = False)
            elif "setRelay" in newMqttMessageDict["content"]:
                self.setRelayStates(newMqttMessageDict["content"]["setRelay"])

    def threadBreak(self):
        time.sleep(0.3)