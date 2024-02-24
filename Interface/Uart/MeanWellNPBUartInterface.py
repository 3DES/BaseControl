import time
import json
import re
from Base.Supporter import Supporter
from Base.CEnum import CEnum
import Base.Crc
import colorama

from Interface.Uart.SLCanUartInterface import SLCanUartInterface
from Charger.MeanWellNPB import MeanWellNPB


class MeanWellNPBUartInterface(SLCanUartInterface):
    '''
    classdocs
    '''
    CAN_COMMAND_NAMES    = MeanWellNPB.CAN_COMMAND_NAMES
    CAN_COMMANDS         = MeanWellNPB.CAN_COMMANDS
    CHARGER_ADDR_BASE    = MeanWellNPB.CHARGER_ADDR_BASE
    CONTROLLER_ADDR_BASE = MeanWellNPB.CONTROLLER_ADDR_BASE

    POLLING_TIMEOUT = 1      # 1 second should be enough for the device to send an answer since we have always to wait this time even if there is no device with current address!
    COMMUNICATION_ERROR_REPETITIONS = 3

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        if not self.tagsIncluded(["pollingPeriod"], intIfy = True, optional = True):
            self.configuration["pollingPeriod"] = 5 * 60     # default value if not given, 5 minutes should be OK

        if not self.tagsIncluded(["initiallyOff"], optional = True):
            self.configuration["initiallyOff"] = True

        self.READ_TIMEOUT = 5       # if there was no data from easy meter after 5 seconds read will be stopped and thread loop will be left, so there will be no message for that turn!
        self.foundDevices = []


    def _getCommandOpcode(self, command : str) -> str:
        opcode = self.CAN_COMMANDS[command]['opcode']
        changedByteOrder = ((opcode & 0xFF) << 8) | ((opcode & 0xFF00) >> 8)
        return f"{changedByteOrder:04X}"


    def _setChargingData(self, command, value):
        '''
        If a COMMAND1 has been given the charging data will be filled with given value
        but if a COMMAND2, COMMAND3 or so has been given the given value will be concatenated to the charging data
        '''
        if MeanWellNPB._getTrailingDigits(command) <= 1:
            if self.CAN_COMMANDS[command]["type"] == int and self.CAN_COMMANDS[command]["resolution"]:
                self.chargingData[self.CAN_COMMANDS[command]["valueName"]] = round(value / pow(10, self.CAN_COMMANDS[command]["resolution"]), self.CAN_COMMANDS[command]["resolution"])
            else:
                self.chargingData[self.CAN_COMMANDS[command]["valueName"]] = value
        else:
            if self.CAN_COMMANDS[command]["type"] == str:
                self.chargingData[self.CAN_COMMANDS[command]["valueName"]] += value
            else:
                raise Exception(f"only values for str type commands can be concatenated")


    def _getControllerAddress(self, address : int) -> int:
        return self.CONTROLLER_ADDR_BASE | address


    def _getChargerAddress(self, address : int) -> int:
        return self.CHARGER_ADDR_BASE | address


    def threadInitMethod(self):
        super().threadInitMethod()      # we need the preparation from parental threadInitMethod

        self.chargingData = {}
        self.SUPPORTED_COMMANDS = set()
        commands = [member for member in self.CAN_COMMAND_NAMES]
        for command in commands:
            self.SUPPORTED_COMMANDS.add(MeanWellNPB._cutTrailingDigits(command))        # get all commands, cut trailing digits and add it to a set so that all commands are unique, i.e. there will be one SERIAL even if there is a SERIAL1 and SERIAL2
            if not self.CAN_COMMANDS[command]["valueName"] in self.chargingData:        # each parameter gets initialized once, i.e. only one out of e.g. SERIAL1 and SERIAL2 will be handled here! 
                self.chargingData[self.CAN_COMMANDS[command]["valueName"]] = ""

        addresses = range(4)
        for address in addresses:    # addresses can be 0, 1, 2 or 3
            command = self.CAN_COMMAND_NAMES.OPERATION
            self.flush()
            if self._handleCommand(command = command, address = address, error = False):
                # switch device off if configured (data = 0x00)
                if self.configuration["initiallyOff"] and self.chargingData[self.CAN_COMMANDS[command]["valueName"]] == 1:
                    self._handleCommand(command = command, address = address, data = "00")
                self.foundDevices.append(address)

        if not self.foundDevices:
            raise Exception(f"no Meanwell chargers found")
        if len(self.foundDevices) > 1:
            raise Exception(f"more than one Meanwell charger found, that's currently not supported")
        self.logger.info(self, f"found Meanwell charger at addresses: {self.foundDevices}")


#    def threadBreak(self):
#        pass


#    def threadTearDownMethod(self):
#        pass


#    def threadSimmulationSupport(self):
#        '''
#        Necessary since this thread supports SIMULATE flag
#        '''
#        pass


    def _handleCommand(self, command : str, address : int, data : str = None, error : bool = True) -> bool:
        '''
        Handles one SLCan command
        
        @param command      command to be handled (see self.SUPPORTED_COMMANDS)
        @param address      address of the device the command should be sent to
        @param data         data to be send, if no data has been given command is a request command, otherwise it's a set command
        @param error        if error is False, retry is disabled and no error or warning will be generated in case of error (useful e.g. for initial device search)
        @result             True in case answer for request command could have been received or set command had to be handled (since there is no response)
        '''
        # empty string and None means the same
        if data is not None and not len(data):
            data = None

        success = True

        supportedCommands = [member for member in self.CAN_COMMAND_NAMES]
        supportedCommands.sort()
        for supportedCommand in supportedCommands:
            if command == MeanWellNPB._cutTrailingDigits(supportedCommand):
                self.logger.debug(self, f"handle command [{command}/{supportedCommand}]")      # debug message
                # given command has been found (or a similar one, i.e. SERIAL1 instead of SERIAL)

                # check and prepare data if necessary
                sendData = None
                if data is not None:
                    # read only commands cannot be used if data has been given! 
                    if self.CAN_COMMANDS[supportedCommand]["readOnly"]:
                        raise Exception(f"command [{command}/{supportedCommand}] is read only but data [{data}] to write has been given")

                    # try to find correct conversation method and convert data to be sent to Meanwell charger
                    if self.CAN_COMMANDS[supportedCommand]["type"] == int:
                        # convert integer to hex string and change byte order
                        sendData = data

                        # enlarge string so that it fits the command data
                        if len(sendData) % 2:
                            sendData = "0" + sendData
                        if len(sendData) < self.CAN_COMMANDS[supportedCommand]["bytes"] * 2:
                            sendData = "0" * ((self.CAN_COMMANDS[supportedCommand]["bytes"] * 2) - len(sendData))
                        sendData = str(Supporter.changeByteOrderOfHexString(bytes(sendData, 'utf-8')), 'utf-8')
                    #elif callable(self.CAN_COMMANDS[supportedCommand]["type"]):
                    #    # use given convert function
                    #    self._setChargingData(supportedCommand, self.CAN_COMMANDS[supportedCommand]["type"](self, command = supportedCommand, data = data, reverse = True))
                    else:
                        raise Exception(f"unknown data type {self.CAN_COMMANDS[command]['type']} found for command {command}")

                # get opcode in correct byte order
                commandOpcode = self._getCommandOpcode(supportedCommand)

                executionCounter = self.COMMUNICATION_ERROR_REPETITIONS
                while executionCounter:
                    self.sendFrame(command = commandOpcode, address = self._getControllerAddress(address), data = sendData)

                    # was it a request command (means len(data) == 0) then a serial read is necessary
                    if data is None:
                        if match := self.readFrame(address = self._getChargerAddress(address), timeout = self.POLLING_TIMEOUT):
                            if commandOpcode != Supporter.bytesToStr(match['command']):
                                raise Exception(f"unknown data type {self.CAN_COMMANDS[command]['type']} found for command {command}")

                            if command == "ID":
                                # for debugging set a break point here...
                                pass

                            # try to find correct conversation method and fill value into charging data structure
                            if self.CAN_COMMANDS[supportedCommand]["type"] == str:
                                # convert byte array to string and then string to hex byte array (don't be confused, it's Python after all!)
                                self._setChargingData(supportedCommand, Supporter.hexStrToAscii(match['data']))      # fill value into chargingData structure
                            elif self.CAN_COMMANDS[supportedCommand]["type"] == int:
                                # convert hex string to integer
                                self._setChargingData(supportedCommand, int(Supporter.changeByteOrderOfHexString(match['data']), 16))
                            elif callable(self.CAN_COMMANDS[supportedCommand]["type"]):
                                # use given convert function
                                self._setChargingData(supportedCommand, self.CAN_COMMANDS[supportedCommand]["type"](self, supportedCommand, match['data']))
                            else:
                                raise Exception(f"unknown data type {self.CAN_COMMANDS[command]['type']} found for command {command}")
                            executionCounter = 0        # stop error repetition loop
                        else:
                            success = False
                            if not error:
                                executionCounter = 0
                            else:
                                executionCounter -= 1
                                if not executionCounter:
                                    errorMessage = f"response missed for request command [{command}] too often, stop command execution"
                                    if self.CAN_COMMANDS[supportedCommand]["errorOnNoResponse"]:
                                        self.logger.error(self, errorMessage)
                                    else:
                                        self.logger.warning(self, errorMessage)
                                else:
                                    self.logger.warning(self, f"response missed for request command [{command}], repeat command")
                    else:
                        executionCounter = 0    # stop error repetition loop
                #break   # no break here since a command, e.g. ID can require several commands, e.g. ID1 and ID2 to be executed
        return success


    def _handleAllCommands(self, address : int):
        '''
        Read all existing values and fill charging structure of device at given address
        '''
        for command in self.SUPPORTED_COMMANDS:
            self._handleCommand(command, address)


    def threadMethod(self):
        refresh = False
        # handle requests
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "cmd" in newMqttMessageDict["content"] and "address" in newMqttMessageDict["content"]:
                command = newMqttMessageDict["content"]["cmd"]
                address = newMqttMessageDict["content"]["address"]

                if address not in self.foundDevices:
                    raise Exception(f"cannot handle command {command} sincer there is no device at address {address}")

                # if command has a trailing number remove it since e.g. ID1 means ID, SERIAL2 means SERIAL, ...
                command = MeanWellNPB._cutTrailingDigits(command)
                if command in self.SUPPORTED_COMMANDS:
                    data = None
                    if "data" in newMqttMessageDict["content"]:
                        data = newMqttMessageDict["content"]["data"]

                    self._handleCommand(command, address, data)     # send telegram
                    if data is not None:
                        self._handleCommand(command, address)       # auto readback
                else:
                    raise Exception(f"unknown command [{command}] given, supported commands are {[self.SUPPORTED_COMMANDS]}")
                refresh = True
            else:
                raise Exception(f"unknown message received: [{newMqttMessageDict['content']}]")

        # handle auto polling
        if self.timer(name = "pollingTimer", timeout = self.configuration["pollingPeriod"], firstTimeTrue = True, autoReset = True):
            for address in self.foundDevices:
                #self._handleCommand("CHG_STATUS", address)  # only to test one command without long waiting time
                self._handleAllCommands(address)
            refresh = True

        if refresh:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargingData, globalPublish = False, enableEcho = False)

