import time
import json

from Interface.Uart.BasicUartInterface import BasicUartInterface
from Base.Supporter import Supporter

class UsbRelaisUartInterface(BasicUartInterface):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.separator = b" "
        self.comandEnd = b"\n"
        self.firstLoop = True

    def readRelayState(self):

        relays = {"Relay1": "unknown", "Relay2": "unknown", "Relay3": "unknown", "Relay4": "unknown"}
        zeilen = []

        self.serialReset_input_buffer()
        self.serialWrite(b"getIO\n")
        # Die nächsten 8 Zeilen lesen
        for i in range(8):
            zeilen.append("")
            zeilen[i] = self.serialReadLine()

        for i in zeilen:
            y = i.split()
            # RelayLock deaktivieren sonst können keine Relais geschaltet werden
            if i == b"RelayLock 1\r\n":
                self.serialWrite(b"RelayLock 0\n")
                self.logger.info(self, "UsbRel Lock released.") 
            if len(y) > 0:
                if y[0].decode() in relays:
                    relays[y[0].decode()] = y[1].decode()
        return relays

    def sendRelayState(self, RelayState):
        for relay in list(RelayState):
            self.serialWrite(Supporter.encode(relay) + self.separator + Supporter.encode(RelayState[relay]) + self.comandEnd)

    def threadMethod(self):
        if self.firstLoop:
            self.firstLoop = False
            self.readRelayState()
            self.sendRelayState({"Relay1": "0", "Relay2": "0", "Relay3": "0", "Relay4": "0"})

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if "cmd" in newMqttMessageDict["content"]:
                if "readRelayState" == newMqttMessageDict["content"]["cmd"]:
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.readRelayState(), globalPublish = False, enableEcho = False)
            elif "setRelay" in newMqttMessageDict["content"]:
                self.sendRelayState(newMqttMessageDict["content"]["setRelay"])

    def threadBreak(self):
        time.sleep(0.1)