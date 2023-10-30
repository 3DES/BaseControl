import time
import struct
import math
from Interface.Uart.BasicUartInterface import BasicUartInterface
from Base.Supporter import Supporter
import colorama
import sys


class DalyBmsUartInterface(BasicUartInterface):
    '''
    classdocs
    
    based on https://github.com/dreadnought/python-daly-bms commit da769999d8
    '''


    _ERROR_REPEATS = 40         # in case of communication error 20 repeats will be done before an exception is thrown



    """
    The error messages are taken from the "Part 4_ Daly RS485+UART Protocol.pdf",
    so the translation quality isn't that great yet.
    """
    ERROR_CODES = {
        0: [
                "warning of cell over voltage, level 1",
                "warning of cell over voltage, level 2",
                "warning of cell under voltage, level 1",
                "warning of cell under voltage, level 2",
                "warning of battery over voltage, level 1",
                "warning of battery over voltage, level 2",
                "warning of battery under voltage, level 1",
                "warning of battery under voltage, level 2",
            ],
        1: [
                "charging over-temperature, level 1",
                "charging over-temperature, level 2",
                "charging under-temperature, level 1",
                "charging under-temperature, level 2",
                "discharging over-temperature, level 1",
                "discharging over-temperature, level 2",
                "discharging under-temperature, level 1",
                "discharging under-temperature, level 2",
            ],
        2: [
                "charge over current, level 1",
                "charge over current, level 2",
                "discharge over current, level 1",
                "discharge over current, level 2",
                "SOC too high alarm, level 1",
                "SOC too high alarm, level 2",
                "SOC too low alarm, level 1",
                "SOC too low alarm, level 2",
            ],
        3: [
                "voltage difference alarm, level 1",
                "voltage difference alarm, level 2",
                "temperature difference alarm, level 1",
                "temperature difference alarm, level 2",
            ],
        4: [
                "charging  MOS over-temperature warning",
                "discharge MOS over-temperature warning",
                "charging MOS temperature sensor failure",
                "discharge MOS temperature sensor failure",
                "charging MOS adhesion failure",
                "discharge MOS adhesion failure",
                "charging MOS open circuit failure",
                "discharge MOS open circuit failure",
            ],
        5: [
                "AFE acquisition chip malfunction",
                "voltage collect drop off",
                "cell temperature sensor Fault",
                "EEPROM error",
                "RTC malfunction",
                "precharge failure",
                "communications failure",
                "internal communication failure",
            ],
        6: [
                "current module failure",
                "battery voltage detection fault",
                "short circuit protection fault",
                "low voltage forbidden charge fault",
                "RESERVED",
                "RESERVED",
                "RESERVED",
                "RESERVED",
            ],
    }

    ADDRESS = {
        # daly BMS address ids
        "USB"       : 4,
        "Bluetooth" : 8,
    }

    
    WARNING_THRESHOLD = 3
    readRequestFailed = {}


    def __init__(self, threadName : str, configuration : dict):
        super().__init__(threadName, configuration)

        self.removeMqttRxQueue()        # mqttRxQueue not needed so remove it

        self.tagsIncluded(["interfaceType"])
        self.address = self.ADDRESS[self.configuration["interfaceType"]]
        self.tagsIncluded(["errorFilter"], optional = True, default = "")

        self.status = None
        self.toggle = False


    @classmethod
    def _calc_checksum(cls, message_bytes):
        """
        Calculate the checksum of a message
        :param message_bytes: Bytes for which the checksum should get calculated
        :return: Checksum as bytes
        """
        return bytes([sum(message_bytes) & 0xFF])


    def _format_message(self, command, extra=""):
        """
        Takes the command ID and formats a request message
        :param command: Command ID ("90" - "98")
        :return: Request message as bytes
        """
        # 95 -> a58095080000000000000000c2
        message = f"a5{self.address}0{command}08{extra}"
        message = message.ljust(24, "0")
        message_bytes = bytearray.fromhex(message)
        message_bytes += self._calc_checksum(message_bytes)
        self.logger.debug(self.name, f"sent cmd:[{command}] message:[{message_bytes.hex()}]")
        return message_bytes


    def _read_request(self, command, extra = "", max_responses = 1, return_list = False, timeout : int = 1):
        """
        Sends a read request to the BMS and reads the response. In case it fails, it retries 'max_responses' times.
        :param command: Command ID ("90" - "98")
        :param max_responses: For how many response packages it should wait (Default: 1).
        :return: Request message as bytes or False
        """
        response_data = None

        response_data = self._read(
            command = command,
            extra = extra,
            max_responses = max_responses,
            return_list = return_list,
            timeout = timeout
        )

        if not response_data:
            if command not in self.readRequestFailed:
                self.readRequestFailed[command] = 0
            self.readRequestFailed[command] += 1
            
            # there are a lot of failed communications so only show a warning if three or more in a row failed, otherwise show an info message
            if self.readRequestFailed[command] >= self.WARNING_THRESHOLD:
                self.logger.warning(self.name, f'command [{command}] failed {self.readRequestFailed[command]} times')
            else:
                self.logger.debug(self.name, f'command [{command}] failed {self.readRequestFailed[command]} time(s)')

            return False
        else:
            if command in self.readRequestFailed and self.readRequestFailed[command]:
                if self.readRequestFailed[command] >= self.WARNING_THRESHOLD:
                    self.logger.warning(self.name, f'command [{command}] passed again after {self.readRequestFailed[command]} fails')
                else:
                    self.logger.debug(self.name, f'command [{command}] passed again after {self.readRequestFailed[command]} fail(s)')
            self.readRequestFailed[command] = 0

        self.logger.debug(self.name, f'command [{command}], request [{response_data}]')
        return response_data


    def _read(self, command, extra : str = "", max_responses : int = 1, return_list : bool = False, timeout : int = 1):
        RESPONSE_LENGTH = 13

        # throw away any received data
        self.flush()

        # prepare message
        message_bytes = self._format_message(command, extra=extra)

        self.logger.debug(self.name, f"serial write [{message_bytes}]")

        # send message
        if not self.serialWrite(message_bytes):
            self.logger.error(self.name, f"serial write failed for command [{command}]")
            return False
        
        response_data = []
        responses = 0

        startTime = Supporter.getTimeStamp()
        while responses < max_responses:
            if Supporter.getSecondsSince(startTime) > timeout:
                self.logger.debug(self.name, f"leave read loop because of timeout ({timeout}s)")
                break

            receivedBytes = self.serialRead(length = RESPONSE_LENGTH, timeout = timeout)

            # read but nth. received, so read again immediately
            if len(receivedBytes) == 0:
                self.logger.debug(self.name, f"empty response for command [{command}] {max_responses} {responses}")
                continue

            # timeout is for each response, so if we expect more than one response reset timeout again
            startTime = Supporter.getTimeStamp()

            self.logger.debug(self.name, f"loop {responses}, received [{receivedBytes.hex()}], length {len(receivedBytes)}")

            # validate checksum
            response_checksum = self._calc_checksum(receivedBytes[:-1])
            if response_checksum != receivedBytes[-1:]:
                deltaSleep = timeout - Supporter.getSecondsSince(startTime)
                self.logger.debug(self.name, f"response checksum mismatch: {response_checksum.hex()} != {receivedBytes[-1:].hex()} / sleep: {deltaSleep}")
                response_data = []
                # error wait for timeout then leave
                time.sleep(deltaSleep)
                break

            # validate header
            header = receivedBytes[0:4].hex()
            if header[4:6] != command:
                deltaSleep = timeout - Supporter.getSecondsSince(startTime)
                self.logger.debug(self.name, f"invalid header {header}: wrong command ({header[4:6]} != {command}) / sleep: {deltaSleep}")
                response_data = []
                # error wait for timeout then leave
                time.sleep(deltaSleep)
                break

            if receivedBytes == RESPONSE_LENGTH:
                deltaSleep = timeout - Supporter.getSecondsSince(startTime)
                self.logger.debug(self.name, f"invalid message length {len(receivedBytes)} / sleep: {deltaSleep}")
                response_data = []
                # error wait for timeout then leave
                time.sleep(deltaSleep)
                break

            # handle data
            data = receivedBytes[4:-1]
            response_data.append(data)

            # increment response counter since another valid response has been received
            responses += 1

        if return_list or len(response_data) > 1:
            return response_data
        elif len(response_data) == 1:
            return response_data[0]
        else:
            return False


    def get_soc(self):
        # SOC of Total Voltage Current
        if not (response_data := self._read_request("90")):
            return False

        parts = struct.unpack('>h h h h', response_data)
        data = {
            "total_voltage": parts[0] / 10,
            # "x_voltage": parts[1] / 10, # always 0
            "current": (parts[2] - 30000) / 10,  # negative=charging, positive=discharging
            "soc_percent": parts[3] / 10
        }
        return data


    def get_cell_voltage_range(self):
        # Cells with the maximum and minimum voltage
        if not (response_data := self._read_request("91")):
            return False

        parts = struct.unpack('>h b h b 2x', response_data)
        data = {
            "highest_voltage": parts[0] / 1000,
            "highest_cell": parts[1],
            "lowest_voltage": parts[2] / 1000,
            "lowest_cell": parts[3],
        }
        return data


    def get_temperature_range(self):
        # Temperature in degrees celsius
        if not (response_data := self._read_request("92")):
            return False

        parts = struct.unpack('>b b b b 4x', response_data)
        data = {
            "highest_temperature": parts[0] - 40,
            "highest_sensor": parts[1],
            "lowest_temperature": parts[2] - 40,
            "lowest_sensor": parts[3],
        }
        return data

    def get_mosfet_status(self):
        # Charge/discharge, MOS status
        if not (response_data := self._read_request("93")):
            return False

        parts = struct.unpack('>b ? ? B l', response_data)

        if parts[0] == 0:
            mode = "stationary"
        elif parts[0] == 1:
            mode = "charging"
        else:
            mode = "discharging"

        data = {
            "mode": mode,
            "charging_mosfet": parts[1],
            "discharging_mosfet": parts[2],
            # "bms_cycles": parts[3], unstable result
            "capacity_ah": parts[4] / 1000,
        }
        return data


    def get_status(self):
        if not (response_data := self._read_request("94")):
            return False

        parts = struct.unpack('>b b ? ? b h x', response_data)
        state_bits = bin(parts[4])[2:]
        state_names = ["DI1", "DI2", "DI3", "DI4", "DO1", "DO2", "DO3", "DO4"]
        states = {}
        state_index = 0
        for bit in reversed(state_bits):
            if len(state_bits) == state_index:
                break
            states[state_names[state_index]] = bool(int(bit))
            state_index += 1
        data = {
            "cells": parts[0],  # number of cells
            "temperatures": parts[1],  # number of sensors
            "charger_running": parts[2],
            "load_running": parts[3],
            # "state_bits": state_bits,
            "states": states,
            "cycles": parts[5],  # number of charge/discharge cycles
        }
        self.status = data
        return data


    def _calc_num_responses(self, status_field, num_per_frame):
        if not self.status:
            self.logger.error(self.name, "get_status has to be called at least once before calling get_cell_voltages")
            return False

        # each response message includes 3 cell voltages
        if self.address == self.ADDRESS["Bluetooth"]:
            # via Bluetooth the BMS returns all frames, even when they don't have data
            if status_field == 'cells':
                max_responses = 11  # 16S BMS sends frames from 01 to 0B = 11 frames, originally this was 16!?
            elif status_field == 'temperatures':
                max_responses = 1   # 16S BMS sends only one frame, originally this was 3!?
            else:
                self.logger.error(self.name, "unkonwn status_field %s" % status_field)
                return False
        else:
            # via UART/USB the BMS returns only frames that have data
            max_responses = math.ceil(self.status[status_field] / num_per_frame)
        return max_responses


    def _split_frames(self, response_data, status_field, structure):
        values = {}
        x = 1
        for response_bytes in response_data:
            parts = struct.unpack(structure, response_bytes)
            if parts[0] != x:
                self.logger.warning(self.name, "frame out of order, expected %i, got %i" % (x, response_bytes[0]))
                continue
            for value in parts[1:]:
                values[len(values) + 1] = value
                if len(values) == self.status[status_field]:
                    return values
            x += 1


    def get_cell_voltages(self):
        if not (max_responses := self._calc_num_responses(status_field="cells", num_per_frame=3)):
            return False
        if not (response_data := self._read_request("95", max_responses=max_responses, return_list=True)):
            return False

        if (cell_voltages := self._split_frames(response_data=response_data, status_field="cells", structure=">b 3h x")) is not None:
            for id in cell_voltages:
                cell_voltages[id] = cell_voltages[id] / 1000
        return cell_voltages


    def get_temperatures(self):
        # Sensor temperatures
        if not (max_responses := self._calc_num_responses(status_field="temperatures", num_per_frame=7)):
            return False
        if not (response_data := self._read_request("96", max_responses=max_responses, return_list=True)):
            return False

        if (temperatures := self._split_frames(response_data=response_data, status_field="temperatures", structure=">b 7b")) is not None:
            for id in temperatures:
                temperatures[id] = temperatures[id] - 40
        return temperatures


    def get_balancing_status(self):
        # Cell balancing status
        if not (response_data := self._read_request("97")):
            return False

        self.logger.debug(self.name, response_data.hex())
        bits = bin(int(response_data.hex(), base=16))[2:].zfill(48)
        self.logger.debug(self.name, bits)
        cells = {}
        for cell in range(1, self.status["cells"] + 1):
            cells[cell] = bool(int(bits[cell * -1]))
        self.logger.debug(self.name, str(cells))
        return cells


    def _disableCharging(self, values : dict, error : str, errorByte : int, errorBit : int, additionalMessage : str):
        self.logger.error(self.name, f"disable charging because of '{error}', (info={additionalMessage}, ErrorBit={errorByte}.{errorBit})")
        values["mosfet_status"]["charging_mosfet"] = False


    def _disableDisCharging(self, values : dict, error : str, errorByte : int, errorBit : int, additionalMessage : str):
        self.logger.error(self.name, f"disable dis-charging because of '{error}', (info={additionalMessage}, ErrorBit={errorByte}.{errorBit})")
        values["mosfet_status"]["discharging_mosfet"] = False


    def _disableChargingAndDisCharging(self, values : dict, error : str, errorByte : int, errorBit : int, additionalMessage : str):
        self._disableCharging(values, errorByte, errorBit, additionalMessage)
        self._disableDisCharging(values, errorByte, errorBit, additionalMessage)


    def _notHandledError(self, values : dict, error : str, errorByte : int, errorBit : int, additionalMessage : str):
        self.logger.error(self.name, f"Not supported error '{error}' found, deactivate it or add error handler for it, (info={additionalMessage}, ErrorBit={errorByte}.{errorBit})")
        raise Exception(f"Not supported error '{error}' found, deactivate it or add error handler for it")


    def get_errors(self):
        '''
        Request error list from daly bms and convert it into byte/bit list for further processing
        @return     False in case of request failed
        @return     [] in case there wasn't any error
        @return     [[byte1,bit1], [byte2,bit2]] list for all found errors that aren't filtered byte configured filter list
        '''
        def getErrorByteBitList(binaryString : str, byte_index : int):
            '''
            Convert given bit string into bit index list and combine it with given byte_index
            @param binaryString  string of bits, e.g. 101101
            @param byte_index    index of the byte the given binaryString represents
            @return    list containing all byte/bit combinations of the set bits in binaryString, e.g. [[1, 1], [1, 4]] for the value 0x12
            '''
            errorByteBitList = []
            for bit_index, bit in enumerate(reversed(binaryString)):        # the reverse operation helps here since the given bit string contains, e.g. "11010", leading ZEROs are missed, and reverse handling from LSB to MSB can stop when there are no further ONE bits 
                if bit == "1":
                    errorByteBitList.append([byte_index, bit_index])
            return errorByteBitList

        def getErrorTextsFromByteBitList(byteBitList : list):
            '''
            Creates a error text list from given byte/bit list
            @
            '''
            errorTexts = []
            for errorByte, errorBit in byteBitList:
                errorTexts.append(self.ERROR_CODES[errorByte][errorBit])
            return errorTexts

        # Battery failure status
        if not (response_data := self._read_request("98")):
            return False        # request failed

        errors = []
        if int.from_bytes(response_data, byteorder='big') == 0:
            return errors       # no error set at all

        filterMask = self.configuration["errorFilter"]

        for byte_index, byteContent in enumerate(response_data):
            # error injection
            #if byte_index == 1:
            #    byteContent = 0x12
            if "errorFilter" in self.configuration:
                if len(filterMask) > (byte_index * 2):
                    filter = int(filterMask[byte_index * 2:(byte_index * 2 + 1) + 1], 16)       # additional +1 since the sub string contains all characters EXCLUSIVE the one at the second index!
                    if (byteContent & filter) != byteContent:
                        inverseFilter = (~filter) & 0xFF    # inverse filter and ignored stuff is for logging only!
                        ignoredErrors = byteContent & inverseFilter
                        remainingErrors = byteContent & filter
                        ignoredErrorBits = bin(ignoredErrors)[2:]     # result is a string, like "0b10010", as you can see the leading ZERO bits are missed but that's not a problem since the bits are handled from LSB to MSB and if there are no further ONE bits we can stop 
                        ignoredErrorsList = getErrorByteBitList(ignoredErrorBits, byte_index)
                        ignoredErrorTexts = getErrorTextsFromByteBitList(ignoredErrorsList)
                        message = f"error byte {byte_index} ignored some errors: 0x{byteContent:02X} & 0x{filter:02X} = 0x{remainingErrors:02X}, ignored error bits = 0x{ignoredErrors:02X} -> {ignoredErrorTexts}"
                        #Supporter.debugPrint(message)
                        self.logger.debug(self.name, message)

                        byteContent = remainingErrors    # set filtered value for further processing

            # continue loop in case there are no error bits set in current handled byte
            if byteContent == 0:
                continue

            bits = bin(byteContent)[2:]     # result is a string, like "0b10010", as you can see the leading ZERO bits are missed but that's not a problem since the bits are handled from LSB to MSB and if there are no further ONE bits we can stop 
            errors += getErrorByteBitList(bits, byte_index)   # concatenate new errors to errors list
            #Supporter.debugPrint(f"bits {bits}, reversed {list(reversed(bits))}, type {type(bits)}, errors {errors}", color = "BLUE")

            self.logger.debug(self.name, f"byteIndex:{byte_index} byteContent:{byteContent} bits:{bits} errors:{errors}")
        return errors


    def set_discharge_mosfet(self, on=True):
        extra = "01" if on else "00"

        if not (response_data := self._read_request("d9", extra = extra)):
            return False
        
        self.logger.debug(self.name, response_data.hex())
        # on response
        # 0101000002006cbe
        # off response
        # 0001000002006c44


    def threadMethod(self):
        keys = [
            "status",
            "soc",               
            "cell_voltage_range",
            "temperature_range",
            "mosfet_status",    
            "cell_voltages",     
            "temperatures",     
            "balancing_status",  
            "errors",  
        ]

        # methods can return an explicit "False" what means communication should be repeated, all other stuff, even empty one means OK
        methods = {
            "status":             self.get_status,
            "soc":                self.get_soc,
            "cell_voltage_range": self.get_cell_voltage_range,
            "temperature_range":  self.get_temperature_range,
            "mosfet_status":      self.get_mosfet_status,
            "cell_voltages":      self.get_cell_voltages,
            "temperatures":       self.get_temperatures,
            "balancing_status":   self.get_balancing_status,
            "errors":             self.get_errors,
        }

        errorHandlers = {
            0: [
                self._disableCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableDisCharging,
                self._disableCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableDisCharging,
            ],
            1: [
                self._disableCharging,
                self._disableCharging,
                self._disableCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableDisCharging,
                self._disableDisCharging,
                self._disableDisCharging,
            ],
            2: [
                self._disableCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableDisCharging,
                self._disableCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableDisCharging,
            ],
            3: [
                # currently we have no idea what to do in case of these errors...
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
                self._notHandledError,
            ],
            4: [
                self._disableCharging,
                self._disableDisCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableCharging,
                self._disableDisCharging,
                self._disableCharging,
                self._disableDisCharging,
            ],
            5: [
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
            ],
            6: [
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
                self._disableChargingAndDisCharging,
            ],
        }

        values = {}

        for key in keys:
            success = False
            self.logger.debug(self.name, f"check: {key}")
            for repeat in range(self._ERROR_REPEATS):
                result = methods[key]()
                self.logger.debug(self.name, f"repeat: {repeat}, cmd: {key}, result: {result}")

                # since result can be empty as well what means OK we have explicitly to check for False!!!
                if (result == False):       # YES, compare explicitly with False here, since it could also be an empty list what has to be handled differently!!!
                    self.logger.debug(self.name, f"request failed once: {result} == False")
                else:
                    values[key] = result
                    success = True
                    break
            if not success:
                raise Exception(f"too many errors for command [{key}] in [{self.name}]")

        # status should be the first one to get number of cells and temp sensors
        #self.logger.debug(self.name, f"status:       " + str(values["status"]))
        #self.logger.debug(self.name, f"voltages:     " + str(values["cell_voltages"]))
        #self.logger.debug(self.name, f"mosfet:       " + str(values["mosfet_status"]))
        #self.logger.debug(self.name, f"temperatures: " + str(values["temperature_range"]))
        #self.logger.debug(self.name, f"balancing:    " + str(values["balancing_status"]))
        #self.logger.debug(self.name, f"errors:       " + str(values["errors"]))

        # take min and max values from BMS
        vMin = values["cell_voltage_range"]["lowest_voltage"]
        vMax = values["cell_voltage_range"]["highest_voltage"]

        # now check if voltage list has a value less or larger than min/max value
        voltageList = []
        
        # @todo folgendes if dient zur Fehlersuche, sobalt Fehler gefunden ist, kann das raus! Gesuchter Fehler liegt in Zeile >>>if (not "cell_voltages" in values) or not len(values["cell_voltages"]):<<< 
        #         File "/share/PowerPlant/Base/ThreadBase.py", line 178, in threadLoop
        #           self.threadMethod()             # execute working method
        #         File "/share/PowerPlant/Interface/Uart/DalyBmsUartInterface.py", line 635, in threadMethod
        #           if (not "cell_voltages" in values) or not len(values["cell_voltages"]):
        #       TypeError: object of type 'NoneType' has no len()
        #        (ThreadBase.py:197)
        # --> siehe fehler_DalyBmsUartInterface_2.txt
        if (not "cell_voltages" in values):
            message = f"values = {values}, type is {type(values)}"
            Supporter.debugPrint(message, color = "BLUE")
            self.logger.error(self.name, message)

        if (not "cell_voltages" in values) or not len(values["cell_voltages"]):
            self.logger.error(self.name, f"received invalid values without \"cell_voltages\" element: {values}")
        for cellNumber, cellVoltage in values["cell_voltages"].items():
            # that a single cell voltage is lower/higher than the overall min/max voltage value is common and happens because of different voltage read times!
            if cellVoltage < vMin:
                #self.logger.info(self.name, f"cell {cellNumber} has lower voltage {cellVoltage} as vMin mentioned by daly bms {vMin}")
                vMin = cellVoltage
            elif cellVoltage > vMax:
                #self.logger.info(self.name, f"cell {cellNumber} has higher voltage {cellVoltage} as vMax mentioned by daly bms {vMax}")
                vMax = cellVoltage
            voltageList.append(cellVoltage)


        errorInjectionTest = 0 # 2, 3, ..., 8
        #errorInjectionInterface = "BmsInterfaceAccu1"
        errorInjectionInterface = "BmsInterfaceAccu2"
        if errorInjectionTest:
            if self.name == errorInjectionInterface:
                if self.timer("errorInjection", timeout = 10, autoReset = False):
                    # undervoltage tests
                    if errorInjectionTest == 1:
                        vMin = 2.0
                    elif errorInjectionTest == 2:
                        voltageList[0]  = 1.3
                    elif errorInjectionTest == 3:
                        voltageList[3]  = 1.3
                    elif errorInjectionTest == 4:
                        voltageList[-1] = 1.3
                    # overvoltage tests
                    elif errorInjectionTest == 5:
                        vMax = 4.0
                    elif errorInjectionTest == 6:
                        voltageList[0]  = 4.3
                    elif errorInjectionTest == 7:
                        voltageList[3] = 4.3
                    elif errorInjectionTest == 8:
                        voltageList[-1] = 4.3

                    Supporter.debugPrint(f"ERROR [{errorInjectionTest}] injected for {int(-self.timer('errorInjection', timeout = 10, autoReset = False, remainingTime = True))} seconds", color = f"{colorama.Fore.RED}")

        # @TODO temperaturen auswerten!!!

        if ("errors" in values) and values["errors"]:
            for errorByte, errorBit in values["errors"]:
                if errorHandlers[errorByte][errorBit] is not None:
                    errorHandlers[errorByte][errorBit](values, self.ERROR_CODES[errorByte][errorBit], errorByte, errorBit, f"voltages: {voltageList}")

        chargingOk = values["mosfet_status"]["charging_mosfet"]
        dischargingOk = values["mosfet_status"]["discharging_mosfet"]

        message = {"toggleIfMsgSeen" : self.toggle, "Vmin" : vMin, "Vmax" : vMax, "VoltageList" : voltageList, "BmsEntladeFreigabe" : dischargingOk, "BmsLadeFreigabe" : chargingOk}
        self.toggle = not self.toggle       # toggle our toggle bit, if we are here all values have been read successfully!

        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), message, globalPublish = False)

        self.logger.debug(self.name, str(message))


    def threadBreak(self):
        time.sleep(1)

