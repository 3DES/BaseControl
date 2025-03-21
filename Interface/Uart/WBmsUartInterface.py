import time

from Interface.Uart.BasicUartInterface import BasicUartInterface

class WBmsUartInterface(BasicUartInterface):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''

        # We have to create configuration bevore we call super class. The Parameter configuration have to be given because it doesn't exist yet.
        self.tagsIncluded(["baudrate"], configuration = configuration, optional = True, default = 9600)

        super().__init__(threadName, configuration)
        self.removeMqttRxQueue()
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Ladephase": "none", "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False, "BmsLadeFreigabe":False}


    def threadMethod(self):

        line = self.serialReadLine()
        lastLine = False
        if len(line):
            segmentList = line.split()
            
            try:
                for i in segmentList:
                    if i == b'Kleinste':
                        tempVoltage = float(segmentList[2])
                        if tempVoltage > -5.0 and tempVoltage < 10:         # try to filter invalid data
                            self.BmsWerte["Vmin"] = tempVoltage
                    elif i == b'Groeste':
                        tempVoltage = float(segmentList[2])
                        if tempVoltage > -5.0 and tempVoltage < 10:         # try to filter invalid data
                            self.BmsWerte["Vmax"] = tempVoltage
                    elif i == b'Ladephase:':
                        self.BmsWerte["Ladephase"] = segmentList[1].decode()
                        lastLine = True
                        self.serialReset_input_buffer()
                if line == b'Rel fahren 1\r\n':
                    self.BmsWerte["BmsEntladeFreigabe"] = True
                    self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
                elif line == b'Rel fahren 0\r\n':
                    self.BmsWerte["BmsEntladeFreigabe"] = False
                    self.BmsWerte["toggleIfMsgSeen"] = not self.BmsWerte["toggleIfMsgSeen"]
                elif line == b'Rel laden 1\r\n':
                    self.BmsWerte["BmsLadeFreigabe"] = True
                elif line == b'Rel laden 0\r\n':
                    self.BmsWerte["BmsLadeFreigabe"] = False
            except:
                self.logger.warning(self, f"Convert error! {segmentList}")

        if lastLine:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)
    