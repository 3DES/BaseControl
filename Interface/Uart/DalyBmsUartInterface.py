import time
import struct
import math
from Interface.Uart.BasicUartInterface import BasicUartInterface
from Base.Supporter import Supporter


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


    def __init__(self, threadName : str, configuration : dict):
        super().__init__(threadName, configuration)

        self.tagsIncluded(["interfaceType"])
        self.address = self.ADDRESS[self.configuration["interfaceType"]]

        self.status = None


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


    def _read_request(self, command, extra = "", max_responses = 1, return_list = False):
        """
        Sends a read request to the BMS and reads the response. In case it fails, it retries 'max_responses' times.
        :param command: Command ID ("90" - "98")
        :param max_responses: For how many response packages it should wait (Default: 1).
        :return: Request message as bytes or False
        """
        response_data = None

        response_data = self._read (
            command = command,
            extra = extra,
            max_responses = max_responses,
            return_list = return_list
        )

        if not response_data:
            self.logger.warning(self.name, f'command [{command}] failed')
            return False

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
        while True:
            if Supporter.getSecondsSince(startTime) > timeout:
                break

            receivedBytes = self.serialRead(length = RESPONSE_LENGTH, timeout = timeout)

            # nth. received
            if len(receivedBytes) == 0:
                self.logger.debug(self.name, f"empty response for command [{command}] {max_responses} {responses}")
                continue

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

            # expected responses received?
            responses += 1
            if responses >= max_responses:
                break

        if return_list or len(response_data) > 1:
            return response_data
        elif len(response_data) == 1:
            return response_data[0]
        else:
            return False


    def get_soc(self):
        # SOC of Total Voltage Current
        response_data = self._read_request("90")
        if not response_data:
            return False

        parts = struct.unpack('>h h h h', response_data)
        data = {
            "total_voltage": parts[0] / 10,
            # "x_voltage": parts[1] / 10, # always 0
            "current": (parts[2] - 30000) / 10,  # negative=charging, positive=discharging
            "soc_percent": parts[3] / 10
        }
        return data


    def get_cell_voltage_range(self, response_data=None):
        # Cells with the maximum and minimum voltage
        if not response_data:
            response_data = self._read_request("91")
        if not response_data:
            return False

        parts = struct.unpack('>h b h b 2x', response_data)
        data = {
            "highest_voltage": parts[0] / 1000,
            "highest_cell": parts[1],
            "lowest_voltage": parts[2] / 1000,
            "lowest_cell": parts[3],
        }
        return data


    def get_temperature_range(self, response_data=None):
        # Temperature in degrees celsius
        if not response_data:
            response_data = self._read_request("92")
        if not response_data:
            return False
        parts = struct.unpack('>b b b b 4x', response_data)
        data = {
            "highest_temperature": parts[0] - 40,
            "highest_sensor": parts[1],
            "lowest_temperature": parts[2] - 40,
            "lowest_sensor": parts[3],
        }
        return data


    def get_mosfet_status(self, response_data=None):
        # Charge/discharge, MOS status
        if not response_data:
            response_data = self._read_request("93")
        if not response_data:
            return False
        # todo: implement
        self.logger.debug(self.name, response_data.hex())

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


    def get_status(self, response_data=None):
        if not response_data:
            response_data = self._read_request("94")
        if not response_data:
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


    def get_cell_voltages(self, response_data=None):
        if not response_data:
            max_responses = self._calc_num_responses(status_field="cells", num_per_frame=3)
            if not max_responses:
                return
            response_data = self._read_request("95", max_responses=max_responses, return_list=True)
        if not response_data:
            return False

        cell_voltages = self._split_frames(response_data=response_data, status_field="cells", structure=">b 3h x")
        for id in cell_voltages:
            cell_voltages[id] = cell_voltages[id] / 1000
        return cell_voltages


    def get_temperatures(self, response_data=None):
        # Sensor temperatures
        if not response_data:
            max_responses = self._calc_num_responses(status_field="temperatures", num_per_frame=7)
            if not max_responses:
                return
            response_data = self._read_request("96", max_responses=max_responses, return_list=True)
        if not response_data:
            return False

        temperatures = self._split_frames(response_data=response_data, status_field="temperatures",
                                          structure=">b 7b")
        for id in temperatures:
            temperatures[id] = temperatures[id] - 40
        return temperatures


    def get_balancing_status(self, response_data=None):
        # Cell balancing status
        if not response_data:
            response_data = self._read_request("97")
        if not response_data:
            return False
        self.logger.info(self.name, response_data.hex())
        bits = bin(int(response_data.hex(), base=16))[2:].zfill(48)
        self.logger.info(self.name, bits)
        cells = {}
        for cell in range(1, self.status["cells"] + 1):
            cells[cell] = bool(int(bits[cell * -1]))
        self.logger.info(self.name, cells)
        # todo: get sample data and verify result
        return {"error": "not implemented"}


    def get_errors(self, response_data = None):
        # Battery failure status
        if not response_data:
            response_data = self._read_request("98")
        if int.from_bytes(response_data, byteorder='big') == 0:
            return []

        byte_index = 0
        errors = []
        for b in response_data:
            if b == 0:
                byte_index += 1
                continue
            bits = bin(b)[2:]
            bit_index = 0
            for bit in reversed(bits):
                if bit == "1":
                    errors.append(self.ERROR_CODES[byte_index][bit_index])

                bit_index += 1

            self.logger.debug(self.name, "%s %s %s" % (byte_index, b, bits))
            byte_index += 1
        return errors


    def set_discharge_mosfet(self, on=True, response_data=None):
        if on:
            extra = "01"
        else:
            extra = "00"
        if not response_data:
            response_data = self._read_request("d9", extra = extra)
        if not response_data:
            return False
        self.logger.info(self.name, response_data.hex())
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

        expected = {
            "status":             True,
            "soc":                True,
            "cell_voltage_range": True,
            "temperature_range":  True,
            "mosfet_status":      True,
            "cell_voltages":      True,
            "temperatures":       True,
            "balancing_status":   True,
            "errors":             False,        # no error expected
        }

        values = {}

        for key in keys:
            success = False
            self.logger.debug(self.name, f"check: {key}")
            for repeat in range(self._ERROR_REPEATS):
                result = methods[key]()
                self.logger.debug(self.name, f"repeat: {repeat}, cmd: {key}")
                if (result and expected[key]) or ((not result) and (not expected[key])):
                    values[key] = result
                    success = True
                    break
            if not success:
                raise Exception(f"too many errors for command [{key}] in [{self.name}], expected: {expected[key]}")

        # status should be the first one to get number of cells and temp sensors
        self.logger.debug(self.name, f"status:       " + str(values["status"]))
        self.logger.debug(self.name, f"voltages:     " + str(values["cell_voltages"]))
        self.logger.debug(self.name, f"mosfet:       " + str(values["mosfet_status"]))
        self.logger.debug(self.name, f"temperatures: " + str(values["temperature_range"]))
        self.logger.debug(self.name, f"balancing:    " + str(values["balancing_status"]))
        self.logger.debug(self.name, f"errors:       " + str(values["errors"]))


    def threadBreak(self):
        time.sleep(1)

