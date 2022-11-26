import json
import datetime
from Base.ThreadObject import ThreadObject


class UsbRelais(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)




#    def getAndRepairActualMode(self, actualRelaisState):
#        relays = actualRelaisState
#        if relays == {self.relNetzAus: self.aus, self.relPvAus: self.aus, self.relWr2: self.aus, self.relWr1: self.aus}:
#            aktualMode = self.netzMode
#        elif relays == {self.relNetzAus: self.aus, self.relPvAus: self.aus, self.relWr2: self.ein, self.relWr1: self.ein}:
#            aktualMode = self.pvMode
#        elif relays[self.relWr2] == self.ein and relays[self.relWr1] == self.ein:
#            # wenn beide wr an sind und die beiden anderen nur einem zwischenzustand zugeordnet werden können dann schalten wir diese aus
#            myPrint("Error: UsbRel Inconsistent State! Set relNetzAus and relPvAus to off and try again reading state")
#            try:
#                serUsbRel.write(self.relNetzAus + self.aus)
#                serUsbRel.write(self.relPvAus + self.aus)
#                aktualMode = self.unknownMode
#            except:
#                myPrint("Error: UsbRel send Serial failed 3!")                  
#        elif relays == {self.relNetzAus: "unknown", self.relPvAus: "unknown", self.relWr2: "unknown", self.relWr1: "unknown"}:
#            aktualMode = self.unknownMode
#        else:
#            aktualMode = self.modeError
#
#        if meldeStatus == True:
#            myPrint("Info: Die Netz Umschaltung steht jetzt auf %s"%aktualMode)
#
#        if aktualMode == self.modeError:
#            time.sleep(20)
#            aktualMode = self.unknownMode
#            myPrint("Error: UsbRel set all to off and try again reading state")
#            try:
#                serUsbRel.write(self.relNetzAus + self.aus)
#                serUsbRel.write(self.relPvAus + self.aus)
#                serUsbRel.write(self.relWr1 + self.aus)
#                serUsbRel.write(self.relWr2 + self.aus)
#                time.sleep(0.5)
#            except:
#                myPrint("Error: UsbRel send Serial failed 4!")
#        return aktualMode

    def threadInitMethod(self):
        self.mqttPublish(self.interfaceInTopics[0], "readRelayState", globalPublish = False, enableEcho = False)
        #reset triggern
        #auslesen triggern
        pass

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            # check if we got a msg from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                #ausgelesenen wert mit localen vergleichen
                #usblock lösen
                pass
            else:
                if self.name in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], {"cmd":newMqttMessageDict["content"][self.name]}, globalPublish = False, enableEcho = False)

        if self.timer(name = "timerStateReq", timeout = 100):
            self.timer(name = "timerStateReq", remove = True)
            self.mqttPublish(self.interfaceInTopics[0], "readRelayState", globalPublish = False, enableEcho = False)

        # auslesen triggern

