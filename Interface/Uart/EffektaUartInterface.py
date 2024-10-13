import time
from Base.Supporter import Supporter
from Interface.Uart.BasicUartInterface import BasicUartInterface
import Base.Crc

class EffektaUartInterface(BasicUartInterface):
    '''
    classdocs
    examples of commands with crc:
    b'QPIGS\xb7\xa9\r'
    b'QMODI\xc1\r'
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.cmdCounter = 0


    def getEffektaCRC(self, cmd):
        crc = Base.Crc.Crc.crc16XModem(cmd).to_bytes(2,'big')
        crcbytes = bytearray(crc)
        for i in range(len(crcbytes)):
            if crcbytes[i] == 0x0a or crcbytes[i] == 0x0d or crcbytes[i] == 0x28:
                crcbytes[i] = crcbytes[i] + 1
                self.logger.debug(self, "CRCBytes escaped")
        return bytes(crcbytes)


    def getCommand(self, cmdStr):
        cmd = Supporter.encode(cmdStr)
        crc = self.getEffektaCRC(cmdStr)
        cmd = cmd + crc
        cmd = cmd + b'\r'
        return cmd


    def getEffektaData(self, cmd):
        '''
        qery effekta data with given command. Returns the received string if data are ok. Returns a empty string if data are not ok.
        '''

        cmd = self.getCommand(cmd)
        self.logger.debug(self, f"getEffektaData: {cmd}")

        self.serialWrite(cmd)

        serialInput = self.serialReadLine()

        if len(serialInput):
            serialInputByte = bytearray(serialInput)
            lenght = len(serialInputByte)
            receivedCrc = bytearray(b'')
            receivedCrc = serialInputByte[lenght - 3 : lenght - 1]
            del serialInputByte[lenght - 3 : lenght - 0]
    
            if bytes(receivedCrc) == self.getEffektaCRC(Supporter.decode(serialInputByte)):
                del serialInputByte[0]
                data = Supporter.decode(serialInputByte)
                self.logger.debug(self, f"CRC ok. Data: {data}")
                if data == "NAK":
                    return ""
                else:
                    return data
            else:
                self.logger.error(self, f"CRC Error: received: {serialInput}, command: {cmd}, length: {len(serialInput)}")
                return ""
        else:
            self.logger.error(self, f"length error, 0 bytes received, command: {cmd}")
            self.reInitSerial()     # Es gab den Fall, dass die Serial so kaputt war dass sie keine Daten mehr lieferte -> crc error. Es half ein close open
            return ""
            

    def setEffektaData(self, cmd, value = ""):
        
        retVal = self.getEffektaData(cmd + value)
        
        if "ACK" == retVal:
            self.logger.debug(self, "setEffektaData: ok")
            return True
        else:
            self.logger.error(self, f"setEffektaData: failed.-> -cmd: {cmd} -value: {value} -ret: {retVal}")
            return False


    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(exception = False)

            # queryTemplate["query"] = {"cmd":"filledfromSender", "response":"filledFromInterface"}
            # setValueTemplate["setValue"] = {"cmd":"filledfromSender", "value":"filledfromSender", "success": filledFromInterface, "extern":filledfromSender}
            if "query" in newMqttMessageDict["content"]:
                if type(newMqttMessageDict["content"]["query"]) == dict:
                    cmdList = [newMqttMessageDict["content"]["query"]]
                else:
                    cmdList = newMqttMessageDict["content"]["query"]
                for cmd in cmdList:
                    cmd["response"] = self.getEffektaData(cmd["cmd"])
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"query":cmd}, globalPublish = False, enableEcho = False)
            elif "setValue" in newMqttMessageDict["content"]:
                # @todo msg mitloggen, wg schreibzugriffe
                if self.cmdCounter >= 50:
                    raise Exception("Too much commands to inverter per hour!")
                if self.timer(name = "resetMsgCounter", timeout = 60*60):
                    self.timer(name = "resetMsgCounter", remove = True)
                    self.cmdCounter = 0
                if type(newMqttMessageDict["content"]["setValue"]) == dict:
                    cmdList = [newMqttMessageDict["content"]["setValue"]]
                else:
                    cmdList = newMqttMessageDict["content"]["setValue"]
                for cmd in cmdList:
                    self.cmdCounter += 1
                    cmd["success"] = self.setEffektaData(cmd["cmd"], cmd["value"])
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"setValue":cmd}, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(0.4)

    #def threadTearDownMethod(self):
    #    pass

