from Interface.Uart.BasicUartInterface import BasicUartInterface
import time
from GridLoad.SocMeter import SocMeter
from BMS.BasicBms import BasicBms
import Base.Crc
from struct import unpack_from

class JkPbInverterBmsInterface(BasicUartInterface):
    '''
    classdocs
    '''
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        self.tagsIncluded(["baudrate"], configuration = configuration, optional = True, default = 115200)
        super().__init__(threadName, configuration)
        self.BmsWerte = {"VoltageList":[], "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "ChargeDischargeManagement":{"FullChargeRequired":False}, "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False, "BmsLadeFreigabe": False}
        self.FULL_CHG_REQ_TIMER = 60*60*24*30
        self.unique_identifier_tmp = ""
        self.commands = {"command_settings":{"rawCmd":b"\x10\x16\x1e\x00\x01\x02\x00\x00", "respLenght":300, "resptype":1},
                         "command_about":{"rawCmd"   :b"\x10\x16\x1c\x00\x01\x02\x00\x00", "respLenght":300, "resptype":3},
                         "command_status":{"rawCmd": b"\x10\x16\x20\x00\x01\x02\x00\x00", "respLenght":299, "resptype":2}
                        }
        # Data List to ensure that all data arrived and in correct order esp for startup
        # With command_settings we request cell count, which is needed for some calculations
        self.msgTypesMasterMode = ["command_settings", "command_status"]
        self.msgTypesSlaveMode =  ["command_settings", "command_status", "command_about"]
        self.expectedResponsedMsg = {}
        self.localBmsData = []  # List of dict, each dict with data like in self.BmsWerte. If they are complete they will be merged and written in self.BmsWerte

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "address"])
        self.tagsIncluded(["numBatterys"],  optional = True, default = 1)
        if self.configuration["address"] > 0 and self.configuration["numBatterys"] != 1:
            raise Exception("address > 0 and numBatterys != 1 means slave mode is active. We can only read 1 battery in slave mode! Check numBatterys and address in project.json!")
        if self.configuration["numBatterys"] > 1:
            raise Exception("Only one Battery is supported yet. See --todo merger-- in JkPbInverterBmsInterface.py")
        super().threadInitMethod()
        self.initResponseDataList()
        self.initLocalBmsData()
        # self.sendAndCheckCmd(b"\x10\x15\x08\x00\x01\x02\x00\x0F") # set UART3 to DisplayMode schreibt aufs richtige Register setzt aber nicht den richtigen wert 15 laut app

        #self.logger.info(self, f"Bms: {result}")

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "cmd" in newMqttMessageDict["content"]:
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    # Reset FullChgReqTimer because we are in Floatmode now (depending on worker)
                    if self.timerExists("FullChgReqTimer"):
                        self.timer("FullChgReqTimer", remove=True)
        try:
            self.getJkData()
            if self.timerExists("timeoutJkRead"):
                self.timer(name = "timeoutJkRead", remove = True)
        except Exception as e:
            self.logger.error(self, f"Error reading {self.name} inteface. Exception was: {e}")
            if self.timer(name = "timeoutJkRead", timeout = 300):
                raise Exception(f'{self.name} connection to bms: {self.bmsName} is broken since 60s!')

    def threadBreak(self):
        time.sleep(3)

    def sendInternalMqtt(self):
        # If FullChgReqTimer is triggered we send one FullChargeRequired request
        if self.timer("FullChgReqTimer", timeout=self.FULL_CHG_REQ_TIMER):
            self.BmsWerte["ChargeDischargeManagement"]["FullChargeRequired"] = True
        else:
            self.BmsWerte["ChargeDischargeManagement"]["FullChargeRequired"] = False
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)

    def initLocalBmsData(self):
        self.localBmsData =[]
        for _ in range(self.configuration["numBatterys"]):
            self.localBmsData.append({"ChargeDischargeManagement":{}})

    def initResponseDataList(self):
        self.expectedResponsedMsg = {}
        if self.isSlavemode():
            cmdList = self.msgTypesSlaveMode
        else:
            cmdList = self.msgTypesMasterMode

        for cmd in cmdList:
            self.expectedResponsedMsg[cmd] = []
            for _ in range(self.configuration["numBatterys"]):
                self.expectedResponsedMsg[cmd].append(False)

    '''
    xx address
    yy crc from request
    zz messageTypeResponse      (01, 02, 03)
    gg messageTypeRequest       (1E, 20, 1C)
    
    Anfragen an den Slave:
           xx 10 16 gg 00 01 02 00 00 yy yy
           xx 10 16 gg 00 01 02 00 00 yy yy

    Antwort vom Slave (Wenn es einen Master BMS gibt dann frägt dieses selbst ab und wir müssen nur zuhören): 
    addresse in Message von Master (add == xx == 0) welche autonom ohne anfrage gesendet wird:
    55 AA EB 90 zz zz ........ ww xx 10 16 gg 00 01 yy yy /end
    '''

    def read_serial_data(self):
        '''
        read serial data and returns a complete request or response message. Retrun -> bytes
        '''
        #regex = b'(?P<resp>\x55\xaa\xeb\x90.*?\x10\x16(\x1e|\x20|\x1c)\x00\x01..)|(?P<req>.\x10\x16(\x1e|\x20|\x1c)\x00\x01\x02\x00\x00..)'
        regex = b'(?P<resp>\x55\xaa\xeb\x90.*?\x10\x16(\x1e|\x20|\x1c)\x00\x01..)'
        ret = {"data":b'', "type":""}
        if match := self.serialRead(timeout=0.5, regex = regex):
            #if not (match.group('req') is None):
            #    ret["data"] =  match.group('req')
            #    ret["type"] = "req"
            if not (match.group('resp') is None):
                ret["data"] = match.group('resp')
                ret["type"] = "resp"
        return ret

    def send_serial_data_jkbms_pb(self, command: str):
        """
        use the read_serial_data() function to read the data and then do BMS specific checks (crc, start bytes, etc)
        :param command: the command to be sent to the bms
        :return: True if everything is fine, else False
        """
        modbus_msg = bytes([self.configuration["address"]])
        modbus_msg += command
        crc = Base.Crc.Crc.modbusCrc(modbus_msg)
        modbus_msg += crc.to_bytes(2, "little")

        self.serialWrite(modbus_msg)
        self.flush()

    def isSlavemode(self):
        return self.configuration["address"] > 0

    def getAddressFromRequest(self, data):
        return unpack_from("<B", data, 0)[0]

    def isRequest(self, data):
        return data[1] == 0x10 and data[2] == 0x16 and (data[3] == 0x20 or data[3] == 0x1E or data[3] == 0x1C) and data[4] == 0x00 and data[5] == 0x01 and data[6] == 0x02 and data[7] == 0x00 and data[8] == 0x00

    def isResonse(self, data):
        return data[0] == 0x55 and data[1] == 0xAA and data[2] == 0xEB and data[3] == 0x90

    def getResponseType(self, data):
        # caller have to ensure that data is a response
        return unpack_from("<B", data, 4)[0]

    def getAddressFromResponse(self, data):
        # caller have to ensure that data is a response
        # returns address from given response xx
        return unpack_from("<B", data, (len(data)-8))[0]

    def getModbusCrcFromResponse(self, data):
        # caller have to ensure that data is a response
        # returns the repeated crc from request in response yy yy
        return unpack_from("<H", data, (len(data)-2))[0]

    def getModbusDataFromResponse(self, data):
        # caller have to ensure that data is a response 
        # returns the reeated request from a response without crc
        if len(data) > 8:
            return data[(len(data)-8):-2]
        else:
            return data[:-2]

    def checkModbusCrc(self, data):
        return Base.Crc.Crc.modbusCrc(self.getModbusDataFromResponse(data)) == self.getModbusCrcFromResponse(data)

        # caller have to ensure that data is a response
        # returns the reeated request from a response
        length = len(data)
        return data[(len(data)-8):-2]
    def recalculateChargeDischargeManagement(self):
        '''
        if all bms data received then:
        check for each bms if BmsEntladeFreigabe or BmsLadeFreigabe is not set and set charge or disccharge current to 0 in ChargeDischargeManagement List
        check if BMS request floatMode and set voltage (perhaps here or in process.. funktion)
        '''
        for pack in range(len(self.localBmsData)):
            if not self.localBmsData[pack]["BmsLadeFreigabe"]:
                self.localBmsData[pack]["ChargeDischargeManagement"]["ChargeCurrent"] = 0
            if not self.localBmsData[pack]["BmsEntladeFreigabe"]:
                self.localBmsData[pack]["ChargeDischargeManagement"]["DischargeCurrent"] = 0

    def getJkData(self):
        '''
            gets all the BMS data and returns a dict of neccessary data
            In Master Mode we have to listen and in slave mode we have to request data
        '''
        if self.isSlavemode():
            for commandName in self.expectedResponsedMsg:
                self.send_serial_data_jkbms_pb(self.commands[commandName]["rawCmd"])
                time.sleep(0.1) # wait for response
                self.readAndProcessData()
                self.serialReset_input_buffer()
        else:
            # In Master Mode (Address == 0) we only have to listen. The Master Bms will request all the data
            self.readAndProcessData()

    def sendAndCheckCmd(self, cmd):
        if self.isSlavemode():
            self.send_serial_data_jkbms_pb(cmd)
            time.sleep(1) # wait for response 300ms
            response = self.serialRead(timeout=0.5)
            # self.readAndProcessData()
            if len(response) < 5:
                self.logger.error(self, "No data received!")
                self.logger.error(self, f'Error message {self.name} message. Data bullshit! Data was: {response}, dataLen: {len(response["data"])}')
                self.logger.error(self, f'Error message {self.name} message. localBmsData: {self.localBmsData}, cmd: {cmd}')
                self.logger.writeLogBufferToDisk(f"logfiles/{self.name}_JkMessageError.log")
            if not self.checkModbusCrc(response):
                self.logger.error(self, "Wrong crc received. sendAndCheckCmd() ERROR CHECK UNTESTED!!!")
            # todo test crc check
            # todo check data
            '''
            on error example: b'\x01\x90\x03\x0c\x01'
            ok: tx: b'\x01\x10\x15\x08\x00\x01\x02\x00\x00\xe3\xd9'   rx: b'\x01\x10\x15\x08\x00\x01\x84\x07'
            '''
            self.serialReset_input_buffer()
        else:
            raise Exception("WriteCmd isn't tested in Master mode")

    def readAndProcessData(self):
        while(True):
            dataBlock = self.read_serial_data()

            if len(dataBlock["data"]) < 5:
                if self.isSlavemode():
                    self.logger.error(self, "No data received!")
                    self.logger.error(self, f'Error message {self.name} message. Data bullshit! Data was: {dataBlock}, dataLen: {len(dataBlock["data"])}')
                    self.logger.error(self, f'Error message {self.name} message. localBmsData: {self.localBmsData}')
                    self.logger.writeLogBufferToDisk(f"logfiles/{self.name}_JkMessageError.log")
                break

            # Check CRC yy yy in response. This is repeated from request
            if not self.checkModbusCrc(dataBlock["data"]):
                self.logger.error(self, f'Request crc error in response msg (yy yy)! Calculated: {Base.Crc.Crc.modbusCrc(self.getRequestInResponse(dataBlock["data"]))}, From data: {self.getRequestCrcInResponse(dataBlock["data"])}')
                self.logger.error(self, f'Raw data: {dataBlock["data"].hex("-")}')
                break

            if dataBlock["type"] == "resp":
                if self.isSlavemode():
                    localDatalistIndex = 0
                else:
                    localDatalistIndex = self.getAddressFromResponse(dataBlock["data"])
                responseType = self.getResponseType(dataBlock["data"])
                if responseType == self.commands["command_settings"]["resptype"]:
                    self.processSettings(dataBlock["data"], localDatalistIndex)
                    # We got the data and update it in self.BmsWerte
                    self.expectedResponsedMsg["command_settings"][localDatalistIndex] = True
                elif responseType == self.commands["command_about"]["resptype"]:
                    self.processAbout(dataBlock["data"], localDatalistIndex)
                    # We got the data and update it in self.BmsWerte
                    self.expectedResponsedMsg["command_about"][localDatalistIndex] = True
                elif responseType == self.commands["command_status"]["resptype"]:
                    self.processStatus(dataBlock["data"], localDatalistIndex)
                    # We got the data and update it in self.BmsWerte
                    self.expectedResponsedMsg["command_status"][localDatalistIndex] = True
                else:
                    self.logger.error(self, f"Error processing {self.name} message. Unknown data type in response. Data was: {dataBlock}")
            elif dataBlock["type"] == "req":
                self.logger.info(self, f"Request skipped")
            else:
                self.logger.error(self, f"Error handling {self.name} message. Unknown message type. Data was: {dataBlock}")

            if self.localBmsData[localDatalistIndex]["Prozent"] == 0:
                self.logger.error(self, f'Error message {self.name} message. Data bullshit! Data was: {dataBlock}, dataLen: {len(dataBlock["data"])}')
                self.logger.error(self, f'Error message {self.name} message. localBmsData: {self.localBmsData}')
                self.logger.writeLogBufferToDisk(f"logfiles/{self.name}_JkMessageError.log")

            # check if all data were received and toggle the alive bit
            allDataReceived = True
            # todo implement a minBms Parameter to accept offline bms/batterypacks with timeout
            #numBmsPresent = self.expectedResponsedMsg[0].count(True)
            for cmd in list(self.expectedResponsedMsg):
                if not all(self.expectedResponsedMsg[cmd]):
                    allDataReceived = False
                    break

            if allDataReceived:
                self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
                self.initResponseDataList()
                # bevore merging, overwrite some values if neccesary
                self.recalculateChargeDischargeManagement()
                # todo merger für mehrere BMS einbauen, dictmerger funktioniert hier nicht weil es veschiedene MergeMethoden nicht gibt und es subdicts gibt Evtl den merger aus basicBMS als cls method umbauen und verwenden
                #self.BmsWerte.update(BasicBms.dictMerger(self.localBmsData))
                self.BmsWerte.update(self.localBmsData[0])
                self.initLocalBmsData()
                self.serialReset_input_buffer()
                self.sendInternalMqtt()
                break

            # In Slave Mode there is only one response in the buffer
            if self.isSlavemode():
                break


    def processSettings(self, status_data, listIndex):
        messageType = unpack_from("<B", status_data, 4)[0]
        if messageType != self.commands["command_settings"]["resptype"]:
            raise Exception("Got unexpected message")
        VolSmartSleep = unpack_from("<i", status_data, 6)[0] / 1000
        VolCellUV = unpack_from("<i", status_data, 10)[0] / 1000
        VolCellUVPR = unpack_from("<i", status_data, 14)[0] / 1000
        VolCellOV = unpack_from("<i", status_data, 18)[0] / 1000
        VolCellOVPR = unpack_from("<i", status_data, 22)[0] / 1000
        VolBalanTrig = unpack_from("<i", status_data, 26)[0] / 1000
        VolSOC_full = unpack_from("<i", status_data, 30)[0] / 1000
        VolSOC_empty = unpack_from("<i", status_data, 34)[0] / 1000
        VolRCV = unpack_from("<i", status_data, 38)[0] / 1000                   # requested charge voltage boost
        VolRFV = unpack_from("<i", status_data, 42)[0] / 1000                   # requested charge voltage float
        VolSysPwrOff = unpack_from("<i", status_data, 46)[0] / 1000
        CurBatCOC = unpack_from("<i", status_data, 50)[0] / 1000                # max_battery_charge_current
        TIMBatCOCPDly = unpack_from("<i", status_data, 54)[0]
        TIMBatCOCPRDly = unpack_from("<i", status_data, 58)[0]
        CurBatDcOC = unpack_from("<i", status_data, 62)[0] / 1000               # max_battery_discharge_current
        TIMBatDcOCPDly = unpack_from("<i", status_data, 66)[0]
        TIMBatDcOCPRDly = unpack_from("<i", status_data, 70)[0]
        TIMBatSCPRDly = unpack_from("<i", status_data, 74)[0]
        CurBalanMax = unpack_from("<i", status_data, 78)[0] / 1000
        TMPBatCOT = unpack_from("<I", status_data, 82)[0] / 10
        TMPBatCOTPR = unpack_from("<I", status_data, 96)[0] / 10
        TMPBatDcOT = unpack_from("<I", status_data, 90)[0] / 10
        TMPBatDcOTPR = unpack_from("<I", status_data, 94)[0] / 10
        TMPBatCUT = unpack_from("<I", status_data, 98)[0] / 10
        TMPBatCUTPR = unpack_from("<I", status_data, 102)[0] / 10
        TMPMosOT = unpack_from("<I", status_data, 106)[0] / 10
        TMPMosOTPR = unpack_from("<I", status_data, 110)[0] / 10
        CellCount = unpack_from("<i", status_data, 114)[0]
        BatChargeEN = unpack_from("<i", status_data, 118)[0]
        BatDisChargeEN = unpack_from("<i", status_data, 122)[0]
        BalanEN = unpack_from("<i", status_data, 126)[0]
        CapBatCell = unpack_from("<i", status_data, 130)[0] / 1000              # total Capaity in Ah
        SCPDelay = unpack_from("<i", status_data, 134)[0]

        self.cell_count = CellCount
        self.localBmsData[listIndex]["ChargeDischargeManagement"]["ChargeCurrent"] = CurBatCOC
        self.localBmsData[listIndex]["ChargeDischargeManagement"]["DischargeCurrent"] = CurBatDcOC
        # todo set rcv or rfv appending on requested charge mode. Jk publish this via CAN. I couldn't find the bit here.
        #self.localBmsData[listIndex]["ChargeDischargeManagement"]["ChargeVoltage"] = 
        self.localBmsData[listIndex]["ChargeDischargeManagement"]["BoostVoltage"] = round(VolRCV * self.cell_count, 2)
        self.localBmsData[listIndex]["ChargeDischargeManagement"]["FloatVoltage"] = round(VolRFV * self.cell_count, 2)
        #self.localBmsData[listIndex]["ChargeDischargeManagement"]["BoostChargeTime"] = 
        self.localBmsData[listIndex]["ChargeDischargeManagement"]["DischargeVoltage"] = round(VolCellUV * self.cell_count * 1.1, 2)

    def processAbout(self, status_data, listIndex):
        messageType = unpack_from("<B", status_data, 4)[0]
        if messageType != self.commands["command_about"]["resptype"]:
            raise Exception("Got unexpected message")
        serial_nr = status_data[86:97].decode("utf-8")
        vendor_id = status_data[6:18].decode("utf-8")
        hw_version = (status_data[22:26].decode("utf-8") + " / " + status_data[30:35].decode("utf-8")).replace("\x00", "")
        sw_version = status_data[30:34].decode("utf-8")

    def processStatus(self, status_data, listIndex):
        messageType = unpack_from("<B", status_data, 4)[0]
        if messageType != self.commands["command_status"]["resptype"]:
            raise Exception("Got unexpected message")
        if self.cell_count <= 0:
            raise Exception("Could not build cellList. self.cell_count was <= 0")
        # cell voltages
        cellList = []
        for c in range(self.cell_count):
            cellList.append(unpack_from("<H", status_data, c * 2 + 6)[0] / 1000)

        temperatureList = []
        temperatureList.append(unpack_from("<h", status_data, 144)[0] / 10)                     # MOSFET temperature
        temperatureList.append(unpack_from("<h", status_data, 162)[0] / 10)                     # Temperature sensors
        temperatureList.append(unpack_from("<h", status_data, 164)[0] / 10)
        temperatureList.append(unpack_from("<h", status_data, 256)[0] / 10)
        temperatureList.append(unpack_from("<h", status_data, 258)[0] / 10)

#        if unpack_from("<B", status_data, 214)[0] & 0x02:
#            self.to_temperature(1, temperature_1 if temperature_1 < 99 else (100 - temperature_1))
#        if unpack_from("<B", status_data, 214)[0] & 0x04:
#            self.to_temperature(2, temperature_2 if temperature_2 < 99 else (100 - temperature_2))
#        if unpack_from("<B", status_data, 214)[0] & 0x10:
#            self.to_temperature(3, temperature_3 if temperature_3 < 99 else (100 - temperature_3))
#        if unpack_from("<B", status_data, 214)[0] & 0x20:
#            self.to_temperature(4, temperature_4 if temperature_4 < 99 else (100 - temperature_4))

        voltage = unpack_from("<I", status_data, 150)[0] / 1000                            # Battery voltage
        current = unpack_from("<i", status_data, 158)[0] / 1000                            # Battery ampere
        soc = unpack_from("<B", status_data, 173)[0]                                       # SOC
        charge_cycles = unpack_from("<i", status_data, 182)[0]                             # cycles
        capacity_remain = unpack_from("<i", status_data, 174)[0] / 1000                    # capacity
        self.to_protection_bits(unpack_from("<I", status_data, 166)[0])                    # fuses

        # bits
        bal = unpack_from("<B", status_data, 172)[0]
        charge = unpack_from("<B", status_data, 198)[0]
        discharge = unpack_from("<B", status_data, 199)[0]
        charge_fet = 1 if charge != 0 else 0
        discharge_fet = 1 if discharge != 0 else 0
        balancing = 1 if bal != 0 else 0
        #self.BmsWerte = {"VoltageList":[], "Current":0.0, "Prozent":SocMeter.InitAkkuProz, "ChargeDischargeManagement":{"FullChargeRequired":False}, "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False, "BmsLadeFreigabe": False}

        self.localBmsData[listIndex]["VoltageList"] = cellList                                      # -> Ok
        self.localBmsData[listIndex]["Current"] = current                                           # -> Ok
        self.localBmsData[listIndex]["Prozent"] = soc                                               # -> Ok
        self.localBmsData[listIndex]["BmsEntladeFreigabe"] = True if discharge == 1 else False      # -> Ok
        self.localBmsData[listIndex]["BmsLadeFreigabe"] = True if charge == 1 else False            # -> Ok

        # show wich cells are balancing
#        if self.get_min_cell() is not None and self.get_max_cell() is not None:
#            for c in range(self.cell_count):
#                if self.balancing and (self.get_min_cell() == c or self.get_max_cell() == c):
#                    self.cells[c].balance = True
#                else:
#                    self.cells[c].balance = False

    def to_protection_bits(self, byte_data):
        """
        Bit 0x00000001: Wire resistance alarm: 1 warning only, 0 nomal -> OK
        Bit 0x00000002: MOS overtemperature alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000004: Cell quantity alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000008: Current sensor error alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000010: Cell OVP alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000020: Bat OVP alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000040: Charge Over current alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000080: Charge SCP alarm: 1 alarm, 0 nomal -> OK
        Bit 0x00000100: Charge OTP: 1 alarm, 0 nomal -> OK
        Bit 0x00000200: Charge UTP: 1 alarm, 0 nomal -> OK
        Bit 0x00000400: CPU Aux Communication: 1 alarm, 0 nomal -> OK
        Bit 0x00000800: Cell UVP: 1 alarm, 0 nomal -> OK
        Bit 0x00001000: Batt UVP: 1 alarm, 0 nomal
        Bit 0x00002000: Discharge Over current: 1 alarm, 0 nomal
        Bit 0x00004000: Discharge SCP: 1 alarm, 0 nomal
        Bit 0x00008000: Discharge OTP: 1 alarm, 0 nomal
        Bit 0x00010000: Charge MOS: 1 alarm, 0 nomal
        Bit 0x00020000: Discharge MOS: 1 alarm, 0 nomal
        Bit 0x00040000: GPS disconnected: 1 alarm, 0 nomal
        Bit 0x00080000: Modify PWD in time: 1 alarm, 0 nomal
        Bit 0x00100000: Discharg on Faied: 1 alarm, 0 nomal
        Bit 0x00200000: Battery over Temp: 1 alarm, 0 nomal
        """

        # low capacity alarm
        low_soc = (byte_data & 0x00001000) * 2
        # MOSFET temperature alarm
        high_internal_temperature = (byte_data & 0x00000002) * 2
        # charge over voltage alarm
        high_voltage = (byte_data & 0x00000020) * 2
        # discharge under voltage alarm
        low_voltage = (byte_data & 0x00000800) * 2
        # charge overcurrent alarm
        high_charge_current = (byte_data & 0x00000040) * 2
        # discharge over current alarm
        high_discharge_current = (byte_data & 0x00002000) * 2
        # core differential pressure alarm OR unit overvoltage alarm
        cell_imbalance = 0
        # cell overvoltage alarm
        high_cell_voltage = (byte_data & 0x00000010) * 2
        # cell undervoltage alarm
        low_cell_voltage = (byte_data & 0x00001000) * 2
        # battery overtemperature alarm OR overtemperature alarm in the battery box
        high_charge_temperature = (byte_data & 0x00000100) * 2
        low_charge_temperature = (byte_data & 0x00000200) * 2
        # check if low/high temp alarm arise during discharging
        high_temperature = (byte_data & 0x00008000) * 2
        low_temperature = 0
