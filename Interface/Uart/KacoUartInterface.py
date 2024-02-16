import time
import json
import re
from Base.Supporter import Supporter
import Base.Crc
import colorama
from enum import Enum

from Interface.Uart.BasicUartInterface import BasicUartInterface
from Inverter.KacoController import KacoController


class KacoUartInterface(BasicUartInterface):
    '''
    classdocs
    '''
    KACO_VALUE    = KacoController.KACO_VALUE


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.removeMqttRxQueue()        # mqttRxQueue not needed so remove it

        if not self.tagsIncluded(["pollingPeriod"], intIfy = True, optional = True):
            self.configuration["pollingPeriod"] = 60          # default value if not given is "every second"

        if not self.tagsIncluded(["loadCycle"], intIfy = True, optional = True):
            self.configuration["loadCycle"] = 15 * 60         # default value if not given is "15 minutes"

        if not self.tagsIncluded(["dumpSerial"], optional = True):
            self.configuration["dumpSerial"] = False          # default value if not given is "False"

        # "slaves" configuration has to be given, it's a RS485 bus with one or more slaves connected to it
        self.tagsIncluded(["slaves"])
        self.slaveNames = list(self.configuration["slaves"].keys())
        self.inverters = {}
        for slave in self.slaveNames:
            self.inverters[self.configuration["slaves"][slave]] = {}        # dictionary "addr : {}" 
        self.currentSlaveIndex = 0

        self.READ_TIMEOUT = 5       # if there was no data from any slave after 5 seconds read will be stopped and thread loop will be left, so there will be no message for that turn!

        self.SUPPORTED_INVERTERS = {
            # all supported inverters need a function pointer to their read methods, compatible ones can use existing methods, for others a new one has to be implemented
            "3600xi" : self.standardDataRead,
            "050L32" : self.genericDataRead,
        }


    def threadInitMethod(self):
        super().threadInitMethod()      # we need the preparation from parental threadInitMethod 

        self.received = b""     # collect all received message parts here
        self.kacoData = {}
        self.referenceEnergyLevel = {}
        self.slaveDataBackup = {}


    def searchSlave(self, slave : str, address : int):
        cmd = (f"#{address:02d}9\r").encode('iso-8859-15')
        #cmd = f"#{address:02d}0\n"
        #cmd = "#019\x0D"

        # answer for cmd 9 is identical for all KACO inverters 
        # \x0A*019 3600xi \xAE\x0D    # Kaco Powador 3600xi
        # \x0A*029 3600xi \xAF\x0D    # Kaco Powador 3600xi
        # \x0A*039 050L32 \xZZ\x0D    # Kaco blueplanet 5.0 TL3 M2

        self.serialWrite(cmd)
        serialInput = b""
        serialInput += self.serialRead(timeout = 2, length = 15, dump = self.configuration["dumpSerial"])
        regex = f"\x0A(?P<telegram>\*{address:02d}9 (?P<id>[^ ]+) )(?P<checksum>.)\x0D".encode('iso-8859-15')
        #Supporter.debugPrint([f"slave {slave} at address {address}", f"sent [{Supporter.hexCharDump(cmd)}]", f"received [{Supporter.hexCharDump(serialInput)}]", f"search regex [{regex}]"], color = "LIGHTRED" if not len(serialInput) else "LIGHTBLUE")
        if match := re.search(regex, serialInput):
            calculatedChecksum = sum(match.group('telegram')) & 0xFF
            if ord(match.group('checksum')) == calculatedChecksum:
                inverterId = match.group('id').decode('iso-8859-15')
                Supporter.debugPrint(f"{inverterId} in {list(self.SUPPORTED_INVERTERS.keys())}", color = "LIGHTRED")
                if inverterId in list(self.SUPPORTED_INVERTERS.keys()):
                    return inverterId
                else:
                    self.logger.error(self, f"Not supported inverter found: [{inverterId}]")
            else:
                self.logger.error(self, f"Telegram [{match.group('telegram')}] has invalid checksum, 0x{ord(match.group('checksum')):02X} != 0x{calculatedChecksum:02X}")
        return None


    def standardDataRead(self, slave : str, address : int):
        #LENGTH = 66     # expected message has a length of 66 bytes
        regex = f".*\x0A(?P<telegram>\*{address:02d}0 +(?P<state>\d+) +(?P<voltageDC>\d+\.\d+) +(?P<currentDC>\d+\.\d+) +(?P<powerDC>\d+) +(?P<voltageAC>\d+\.\d+) +(?P<currentAC>\d+\.\d+) +(?P<powerAC>\d+) +(?P<temperature>\d+) +(?P<energy>\d+) +)(?P<checksum>.) +(?P<id>[^ \x0D]+)\x0D".encode('iso-8859-15')
        if match := self.serialRead(timeout = 5, regex = regex, dump = self.configuration["dumpSerial"]):
            #Supporter.debugPrint(f"received [{match.group()}]")
            calculatedChecksum = sum(match.group('telegram')) & 0xFF        # check sum is simple sum over the data
            if calculatedChecksum == ord(match.group('checksum')):
                return {
                    KacoUartInterface.KACO_VALUE.STATE.value       : int(match.group('state')),                   # mandatory
                    KacoUartInterface.KACO_VALUE.U1.value          : round(float(match.group('voltageDC')), 1),
                    KacoUartInterface.KACO_VALUE.I1.value          : round(float(match.group('currentDC')), 2),
                    KacoUartInterface.KACO_VALUE.P1.value          : int(match.group('powerDC')),
                    KacoUartInterface.KACO_VALUE.UN.value          : round(float(match.group('voltageAC')), 1),
                    KacoUartInterface.KACO_VALUE.IN.value          : round(float(match.group('currentAC')), 2),
                    KacoUartInterface.KACO_VALUE.POWER.value       : int(match.group('powerDC')),                 # yes, POWER and P1 are identically here since there is only one MPPT
                    KacoUartInterface.KACO_VALUE.PN.value          : int(match.group('powerAC')),                 # mandatory
                    KacoUartInterface.KACO_VALUE.TEMPERATURE.value : int(float(match.group('temperature'))),      # mandatory
                    KacoUartInterface.KACO_VALUE.ENERGY.value      : int(match.group('energy')),                  # mandatory
                    KacoUartInterface.KACO_VALUE.TYPE.value        : match.group('id').decode('iso-8859-15')      # mandatory
                }
        return None


    def genericDataRead(self, slave : str, address : int):
        #LENGTH = 131    # expected message has a length of 131 bytes
        regex = f".*\x0A(?P<telegram>\*{address:02d}n +20 +(?P<id>[^ \x0D]+) +(?P<state>\d+) +(?P<voltage1DC>\d+\.\d+) +(?P<current1DC>\d+\.\d+) +(?P<power1DC>\d+) +(?P<voltage2DC>\d+\.\d+) +(?P<current2DC>\d+\.\d+) +(?P<power2DC>\d+) +(?P<voltage1AC>\d+\.\d+) +(?P<current1AC>\d+\.\d+) +(?P<voltage2AC>\d+\.\d+) +(?P<current2AC>\d+\.\d+) +(?P<voltage3AC>\d+\.\d+) +(?P<current3AC>\d+\.\d+) +(?P<powerDC>\d+) +(?P<powerAC>\d+) +(?P<cosphi>[^ ]+) +(?P<temperature>\d+\.\d+) +(?P<energy>\d+) +)(?P<checksum>[A-F0-9]{{4}})\x0D".encode('iso-8859-15')
        if match := self.serialRead(timeout = 5, regex = regex, dump = self.configuration["dumpSerial"]):
            #Supporter.debugPrint(f"received [{match.group()}]")
            calculatedChecksum = Base.Crc.Crc.crc16EasyMeter(match.group('telegram'))
            if calculatedChecksum == int(b"0x" + match.group('checksum'), base = 16):       # convert hex string to decimal value and compare it to calculated check sum
                return {
                    KacoUartInterface.KACO_VALUE.STATE.value       : int(match.group('state')),                   # mandatory
                    KacoUartInterface.KACO_VALUE.U1.value          : round(float(match.group('voltage1DC')), 1),
                    KacoUartInterface.KACO_VALUE.I1.value          : round(float(match.group('current1DC')), 2),
                    KacoUartInterface.KACO_VALUE.P1.value          : int(match.group('power1DC')),
                    KacoUartInterface.KACO_VALUE.U2.value          : round(float(match.group('voltage2DC')), 1),
                    KacoUartInterface.KACO_VALUE.I2.value          : round(float(match.group('current2DC')), 2),
                    KacoUartInterface.KACO_VALUE.P2.value          : int(match.group('power2DC')),
                    KacoUartInterface.KACO_VALUE.UN1.value         : round(float(match.group('voltage1AC')), 1),
                    KacoUartInterface.KACO_VALUE.IN1.value         : round(float(match.group('current1AC')), 2),
                    KacoUartInterface.KACO_VALUE.UN2.value         : round(float(match.group('voltage2AC')), 1),
                    KacoUartInterface.KACO_VALUE.IN2.value         : round(float(match.group('current2AC')), 2),
                    KacoUartInterface.KACO_VALUE.UN3.value         : round(float(match.group('voltage3AC')), 1),
                    KacoUartInterface.KACO_VALUE.IN3.value         : round(float(match.group('current3AC')), 2),
                    KacoUartInterface.KACO_VALUE.POWER.value       : int(match.group('powerDC')),
                    KacoUartInterface.KACO_VALUE.PN.value          : int(match.group('powerAC')),                 # mandatory
                    KacoUartInterface.KACO_VALUE.TEMPERATURE.value : int(float(match.group('temperature'))),      # mandatory
                    KacoUartInterface.KACO_VALUE.ENERGY.value      : int(match.group('energy')),                  # mandatory
                    KacoUartInterface.KACO_VALUE.TYPE.value        : match.group('id').decode('iso-8859-15')      # mandatory
                }
        return None


    def readSlave(self, slave : str, address : int):
        cmd = (f"#{address:02d}0\r").encode('iso-8859-15')
        #cmd = "#010\x0D"

        # answer for cmd 0 is standard or generic protocol
        # \x0A*010   4 554.7  0.95   526 227.8  2.04   458  30   7486 \x9D 3600xi\x0D        # Kaco Powador 3600xi --> standard protocol
        # \x0A*020   4 540.0  0.99   534 227.0  2.05   463  30   7530 \x80 3600xi\x0D        # Kaco Powador 3600xi --> standard protocol
        # \x0A*03n 20 050L32 4  384.1  1.26   488    3.3  0.00     0  227.5  0.97  226.3  0.95  227.1  0.93   488   459 1.000  33.1   4964 AF9F\x0D    # Kaco blueplanet 5.0 TL3 M2 --> generic protocol
        #
        # ST1 *A N   S U1     I1     P1  UN1    IN1    PN   T    E    F    WR    ST2
        # \x0A*010   4 554.7  0.95   526 227.8  2.04   458  30   7486 \x9D 3600xi\x0D
        #     ST1 = LF
        #     *   = *
        #     A   = Address
        #     N   = Command
        #     S   = Inverter State
        #     U1  = DC Voltage MPPT1
        #     I1  = DC Current MPPT1
        #     P1  = DC Power MPPT1
        #     UN1 = AC Voltage
        #     IN1 = AC Current
        #     PN  = AC Power
        #     T   = Temperature
        #     E   = Daily Energy
        #     F   = Checksum (1 Byte)
        #     WR  = Inverter type
        #     ST2 = CR
        #
        # ST1 *A N #  WR     S  U1     I1     P1     U2   I2       P2 UN1    IN1   UN2    IN2   UN3    IN3    P     PN  COS    T      E    F   ST2
        # \x0A*03n 20 050L32 4  384.1  1.26   488    3.3  0.00     0  227.5  0.97  226.3  0.95  227.1  0.93   488   459 1.000  33.1   4964 AF9F\x0D
        #     ST1 = LF
        #     *   = * 
        #     A   = Address 
        #     N   = Command 
        #     #   = Number of elements 
        #     WR  = Inverter type
        #     S   = InverterState 
        #     U1  = DC Voltage MPPT1
        #     I1  = DC Current MPPT1
        #     P1  = DC Power MPPT1
        #     U2  = DC Voltage MPPT2
        #     I2  = DC Current MPPT2
        #     P2  = DC Power MPPT2
        #     UN1 = AC Voltage L1
        #     IN1 = AC Current L1
        #     UN2 = AC Voltage L2
        #     IN2 = AC Current L2
        #     UN3 = AC Voltage L3
        #     IN3 = AC Current L3
        #     P   = DC Power
        #     PN  = AC Power
        #     COS = Cos phi
        #     T   = Temperature
        #     E   = Daily Energy
        #     F   = Checksum (1 Byte)
        #     ST2 = CR
        #
        # Inverter states (from 3500xi):
        #     0  Inverter just turned on: Only after the initial activation in the morning.
        #     1  Waiting for startup: The self-test has been completed, and the Powador transitions to feed-in operation.
        #     2  Waiting for shutdown. Generator voltage and power are too low: Condition before transitioning to night shutdown.
        #     3  Voltage Regulator: At the start of feeding, power is briefly supplied with a constant generator voltage (80% of the measured idle voltage).
        #     4  MPP tracker continuous search: During low irradiation, feeding is done with a searching MPP controller.
        #     5  MPP tracker no search: During high irradiance, feeding is done for maximum yield.
        #     6  Waiting mode before feeding, testing network and solar voltage: The inverter waits until the generator voltage exceeds the activation threshold (410 V) and then starts the self-test of relays after 3 minutes, checking the network voltages.
        #     7  Waiting mode before self-test, testing network and solar voltage: The inverter waits until the generator voltage exceeds the activation threshold (410 V) and then starts the self-test of relays after 3 minutes, checking the network voltages.
        #     8  Relay self-test: Checking the network relays before the start of feeding.
        #     10 Overtemperature shutdown: In case of overheating of the inverter (>80°C) due to constant overload and lack of air circulation, the inverter shuts down. Causes: too much solar power, too high ambient temperature, inverter defect.
        #     11 Power limitation: Protective function of the inverter when too much generator power is supplied or the device's heat sink has exceeded 75°C.
        #     12 Overload shutdown: Protective function of the inverter when too much generator power is supplied.
        #     13 Overvoltage shutdown: Protective function of the inverter when network voltage L1 is too high.
        #     14 Grid failure (3-phase monitoring): Protective function of the inverter when one of the three phases has failed or the voltage is outside the tolerance.
        #     15 Transition to night shutdown: "Inverter goes to sleep."
        #     18 AFI shutdown: "Residual current too high."
        #     19 Low insulation resistance: Insulation resistance from PV-/PV+ to PE is too low.
        #     30 Measurement technology error: The current and voltage measurements in the inverter are not plausible.
        #     31 AFI module error: An error occurred in the residual current protective module.
        #     32 Self-test error: An error occurred during the network relay check.
        #     33 DC feeding error: The DC feeding into the grid was too high.
        #     34 Communication error: An error occurred in the internal data transmission.

        self.serialWrite(cmd)
        # call handler for detected KACO inverter type at given address
        if serialInput := self.SUPPORTED_INVERTERS[self.inverters[address]["type"]](slave = slave, address = address):
            # print sent and received stuff for better debugging if enabled
            if self.configuration["dumpSerial"]:
                Supporter.debugPrint([f"slave {slave} at address {address}", f"sent [{Supporter.hexCharDump(cmd)}]", f"received [{serialInput}]"], color = "LIGHTRED" if not len(serialInput) else "LIGHTBLUE")
            return serialInput


    def threadBreak(self):
        time.sleep(self.configuration["pollingPeriod"])


#    def threadTearDownMethod(self):
#        pass


#    def threadSummulationSupport(self):
#        '''
#        Necessary since this thread supports SIMULATE flag
#        '''
#        pass


    def threadMethod(self):
        #for slave in self.configuration["slaves"].keys():
        #address = int(self.configuration['slaves'][slave])
        slave   = self.slaveNames[self.currentSlaveIndex]
        address = self.configuration["slaves"][slave]

        if address not in self.inverters or "type" not in self.inverters[address]:  
            # first try to read inverter types (some inverters switch to sleep mode without any communication, in that case try it until an answer has been received)
            if inverterType := self.searchSlave(slave, address):
                self.inverters[address] = { "type" : inverterType }
                Supporter.debugPrint(f"[{address}]:[{self.inverters[address]}]")
        else:
            # all further turns read data from inverters
            if slaveData := self.readSlave(slave, address):
                # data is new (first data package ever received) or data is different from last received data
                if (not address in self.kacoData) or (slaveData != self.kacoData[address]):
                    #Supporter.debugPrint(f"update data: {slaveData} =?= {self.kacoData[address]}", color = "MAGENTA")
                    if (not address in self.kacoData):
                        Supporter.debugPrint(f"new data: {slaveData}", color = "MAGENTA")
                    elif  (slaveData != self.kacoData[address]):
                        Supporter.debugPrint(f"changed data: {slaveData} =?= {self.kacoData[address]}", color = "MAGENTA")
                    self.kacoData[address] = slaveData              # store new data
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.kacoData[address] | {"slave" : slave, "address" : address}, globalPublish = False, enableEcho = False)
                elif (address in self.kacoData) and (slaveData == self.kacoData[address]):
                    Supporter.debugPrint(f"same data: {slaveData} == {self.kacoData[address]}", color = "MAGENTA")

        # select next parametrized slave, when all are handled turn over and start with first one again
        if (self.currentSlaveIndex < len(self.slaveNames) - 1):
            self.currentSlaveIndex += 1
        else:
            self.currentSlaveIndex = 0
            Supporter.debugPrint(f"found KACO inverters [{self.inverters}]")

