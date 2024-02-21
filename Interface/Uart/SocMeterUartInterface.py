import time

from GridLoad.SocMeter import SocMeter
from Interface.Uart.BasicUartInterface import BasicUartInterface

class SocMeterUartInterface(BasicUartInterface):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        
        self.SocMonitorWerte = {"Ah":-1, "Current":0, "Prozent":SocMeter.InitAkkuProz}
        self.cmdList = []


    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "Prozent" in newMqttMessageDict["content"]:
                self.cmdList.append("setSocToValue")
                self.cmdList.append(str(newMqttMessageDict["content"]["Prozent"]))
                self.SocMonitorWerte["Prozent"] = newMqttMessageDict["content"]["Prozent"]
            elif "cmd" in newMqttMessageDict["content"]:
                # If cmd is resetSoc we add a special cmd socResetMaxAndHold, else we add all cmd to cmdList {"cmd":["",""]} and {"cmd":""} is accepted
                if newMqttMessageDict["content"]["cmd"] == "resetSoc":
                    self.cmdList.append("socResetMaxAndHold")
                elif newMqttMessageDict["content"]["cmd"] == list:
                    self.cmdList += newMqttMessageDict["content"]["cmd"]
                else:
                    self.cmdList.append(newMqttMessageDict["content"])

        """
        Message we get from Monitor
        # b'Current A -1.92\r\n'
        # b'SOC Ah 258\r\n'
        # b'SOC <upper Bytes!!!> mAsec 931208825\r\n'
        # b'SOC Prozent 99\r\n'
        
        # supported commands: "config, socResetMax, socResetMin, socResetMaxAndHold, releaseMaxSocHold, setSocToValue"
        """

        line = self.serialReadLine()
        lastLine = False
        if len(line):
            segmentList = line.split()
            try:
                for i in segmentList:
                    if i == b'Current' and segmentList[1] == b'A':
                        self.SocMonitorWerte["Current"] = float(segmentList[2].decode())
                    elif i == b'Prozent':
                        # Wenn wir einen Akkustand haben und der SOC Monitor neu gestartet wurde dann schicken wir den Wert
                        if self.SocMonitorWerte["Prozent"] != SocMeter.InitAkkuProz and int(segmentList[2].decode()) == 0 and self.SocMonitorWerte["Prozent"] != int(segmentList[2].decode()):
                            self.cmdList.append("setSocToValue")
                            self.cmdList.append(str(self.SocMonitorWerte["Prozent"]))
                            self.logger.error(self, f'Error: SocMonitor hatte unerwartet den falschen Wert! Alt: {int(segmentList[2].decode())}, Neu: {self.SocMonitorWerte["Prozent"]}')
                        else:
                            self.SocMonitorWerte["Prozent"] = int(segmentList[2].decode())  
                        # Todo folgende Zeile entfernen und serial vernünftig lösen (zu langsam)
                        self.serialReset_input_buffer()
                        lastLine = True
                    elif i == b'Ah':
                        self.SocMonitorWerte["Ah"] = float(segmentList[2].decode())
            except:
                self.logger.warning(self, f"Convert error!")

        while len(self.cmdList):
            tempcmd = self.cmdList[0]
            try:
                cmd = tempcmd.encode('utf-8')
            except:
                self.logger.error(self, f"Only commands in a list are accepted! We got a {type(self.cmdList)} with following content: {str(self.cmdList)}")
                self.cmdList = []
                break

            cmd = cmd + b'\n'
            self.serialWrite(cmd)
            del self.cmdList[0]

        if lastLine:
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = False, enableEcho = False)

