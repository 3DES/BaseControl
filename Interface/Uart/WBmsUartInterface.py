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
        super().__init__(threadName, configuration)
        self.BmsWerte = {"Vmin": 0.0, "Vmax": 6.0, "Ladephase": "none", "toggleIfMsgSeen":False, "BmsEntladeFreigabe":False}


    def threadMethod(self):

        line = self.serialReadLine()
        lastLine = False
        if len(line):
            segmentList = line.split()
            try:
                for i in segmentList:
                    if i == b'Kleinste':
                        self.BmsWerte["Vmin"] = float(segmentList[2])
                    elif i == b'Groeste':
                        self.BmsWerte["Vmax"] = float(segmentList[2])
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
            except:
                self.logger.warning(self, f"Convert error!")

        if lastLine:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.BmsWerte, globalPublish = False, enableEcho = False)
    