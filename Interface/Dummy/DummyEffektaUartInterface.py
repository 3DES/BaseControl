import json
from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter
from Inverter.EffektaController import EffektaController


class DummyEffektaUartInterface(InterfaceBase):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

    def threadInitMethod(self):
        self.Netzbetrieb = False
        self.battCap = 0
        pass

    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message

            try:
                newMqttMessageDict["content"] = self.extendedJson.parse(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                self.logger.error(self, f'Cannot convert {newMqttMessageDict["content"]} to dict')

            self.logger.debug(self, " received queue message :" + str(newMqttMessageDict))
            # queryTemplate["query"] = {"cmd":"filledfromSender", "response":"filledFromInterface"}
            # setValueTemplate["setValue"] = {"cmd":"filledfromSender", "value":"filledfromSender", "success": filledFromInterface, "extern":filledfromSender}
            if "query" in newMqttMessageDict["content"]:
                if type(newMqttMessageDict["content"]["query"]) == dict:
                    cmdList = [newMqttMessageDict["content"]["query"]]
                else:
                    cmdList = newMqttMessageDict["content"]["query"]
                for cmd in cmdList:
                    if cmd["cmd"] == "QPIGS":
                        if self.battCap == 50:
                            self.battCap = 30
                        else:
                            self.battCap = 50
                        if self.timer(name = "floatModetimer", timeout = 30):
                            self.timer(name = "floatModetimer", remove = True)
                            floatMode = 1
                        else:
                            floatMode = 0
                        if self.Netzbetrieb:
                            cmd["response"] = f"231.6 50.0 000.0 00.0 0000 0000 000 000 49.70 000 0{self.battCap} 0019 0000 055.1 49.81 00000 00100110 00 00 00000 {floatMode}00"
                        else:
                            #(Netzspannung, Netzfrequenz, AcOutSpannung, AcOutFrequenz, AcOutPowerVA, AcOutPower, AcOutLoadProz, BusVoltage, BattSpannung, BattCharge, BattCapacity, InverterTemp, PvCurrent, PvVoltage, BattVoltageSCC, BattDischarge, DeviceStatus1, BattOffset, EeVersion, PvPower, DeviceStatus2) = newMqttMessageDict["content"]["query"]["response"].split()
                            cmd["response"] = f"231.6 50.0 231.6 00.0 0000 0000 000 000 49.70 000 0{self.battCap} 0019 0000 055.1 49.81 00000 00100110 00 00 00000 {floatMode}00"
                    elif cmd["cmd"] == "QMOD":
                        if self.Netzbetrieb:
                            cmd["response"] = "S"
                        else:
                            cmd["response"] = "B"
                    elif cmd["cmd"] == "QMUCHGCR":
                        cmd["response"] = "002 010 030 020 040 050 060"
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {"query":cmd}, globalPublish = False, enableEcho = False)
            elif "setValue" in newMqttMessageDict["content"]:
                if type(newMqttMessageDict["content"]["setValue"]) == dict:
                    cmdList = [newMqttMessageDict["content"]["setValue"]]
                else:
                    cmdList = newMqttMessageDict["content"]["setValue"]
                for cmd in cmdList:
                    if cmd["cmd"] == EffektaController.VerbraucherNetz:
                        self.Netzbetrieb = True
                    elif cmd["cmd"] == EffektaController.VerbraucherAkku:
                        self.Netzbetrieb = False
                    self.logger.info(self, f'set Effekta Parameter: {cmd}')

    #def threadBreak(self):
    #    pass

    #def threadTearDownMethod(self):
    #    pass

