import time
import serial
import crc16

from Base.InterfaceBase import InterfaceBase


class UartInterface(InterfaceBase):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.serialConn = serial.Serial(self.configuration["interface"], self.configuration["baudrate"], timeout=4)
        
    def __delete__(self):
        self.serialConn.close()

    def getEffektaCRC(self, cmd):
        crc = crc16.crc16xmodem(cmd).to_bytes(2,'big')
        crcbytes = bytearray(crc)
        for i in range(len(crcbytes)):
            if crcbytes[i] == 0x0a or crcbytes[i] == 0x0d or crcbytes[i] == 0x28:
                crcbytes[i] = crcbytes[i] + 1
                self.logger.debug(self, "CRCBytes escaped")
        return bytes(crcbytes)

    def getCommand(self, cmd):
        cmd = cmd.encode('utf-8')
        crc = self.getEffektaCRC(cmd)
        cmd = cmd + crc
        cmd = cmd + b'\r'
        return cmd

    def reInitSerial(self):
        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            self.serialConn.close()
            self.serialConn.open()
        except:
            self.logger.error(self, f"Serial Port {self.name} reInit failed!")

    def getEffektaData(self, cmd):
        '''
        qery effekta data with given command. Returns the received string if data are ok. Returns a empty string if data are not ok.
        '''
        
        cmd = self.getCommand(cmd)
        self.logger.debug(self, f"getEffektaData: {cmd}")
        try:
            self.serialConn.write(cmd)

            x = self.serialConn.readline()
        except:
            self.reInitSerial()
            return ""
        
        y = bytearray(x)
        lenght = len(y)
        receivedCrc = bytearray(b'')
        receivedCrc = y[lenght - 3 : lenght - 1]
        del y[lenght - 3 : lenght - 0]
        

        if bytes(receivedCrc) == self.getEffektaCRC(bytes(y)):
            del y[0]
            data = y.decode()
            self.logger.debug(self, f"CRC ok. Data: {data}")
            if data == "NAK":
                return ""
            else:
                return data
        else:
            self.logger.error(self, f"CRC Error: received: {x} command: {cmd}")
            # Es gab den Fall, dass die Serial so kaputt war dass sie keine Daten mehr lieferte -> crc error. Es half ein close open
            if len(x) == 0:
                self.reInitSerial()
            return ""

    def setEffektaData(self, cmd, value = ""):
        
        retVal = self.getEffektaData(cmd + value)
        
        if "ACK" == retVal:
            self.logger.debug(self, "setEffektaData: ok")
            return True
        else:
            self.logger.error(self, f"setEffektaData: failed.-> {cmd} - {value} - {retVal}")
            return False

    #def threadInitMethod(self):
    #    pass

    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.info(self, " received global queue message :" + str(newMqttMessageDict))
            # newMqttMessageDict["query"] = {"cmd":"filledfromSender", "response":"filledFromInterface"}
            # newMqttMessageDict["setValue"] = {"cmd":"filledfromSender", "value":"filledfromSender"}
            if "query" in newMqttMessageDict:
                newMqttMessageDict["query"]["response"] = self.getEffektaData(newMqttMessageDict["query"]["cmd"])
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict, globalPublish = False, enableEcho = False)
            elif "setValue" in newMqttMessageDict:
                newMqttMessageDict["setValue"]["success"] = self.setEffektaData(newMqttMessageDict["setValue"]["cmd"], newMqttMessageDict["setValue"]["value"])
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict, globalPublish = False, enableEcho = False)

    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

