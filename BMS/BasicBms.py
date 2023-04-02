import time
import datetime
import json
from Base.ThreadObject import ThreadObject


class BasicBms(ThreadObject):
    '''
    This class forwards BMS messages to global and noGlobal subscribers. 
    The value have to change in a sensible range/jump to be published globally.
    This class discovers device infos as sensor to a given homeautommation
    This class needs key Vmin, Vmax, BmsEntladeFreigabe and toggleIfMsgSeen in a dict from given BMS interface.
    Optional is Current and Prozent which will be also checked for sensible range/jump.
    Optional is any other Value.
    A global publish is also triggert every 120 seconds
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)


    def checkWerteSprung(self, newValue, oldValue, percent, minVal, maxVal, minAbs = 0):
        
        # Diese Funktion prüft, dass der neue Wert innerhalb der angegebenen maxVal maxVal Grenzen und ausserhalb der angegebenen Prozent Grenze
        # Diese Funktion wird verwendet um kleine Wertsprünge rauszu Filtern und Werte Grenzen einzuhalten

        if newValue == oldValue == 0:
            #myPrint("wert wird nicht uebernommen")
            return False
            
        percent = percent * 0.01
        valuePercent = abs(oldValue) * percent
        
        if valuePercent < minAbs:
            valuePercent = minAbs
            
        minPercent = oldValue - valuePercent
        maxPercent = oldValue + valuePercent
        
        if minVal <= newValue <= maxVal and not (minPercent < newValue < maxPercent):
            #myPrint("wert wird uebernommen")
            return True
        else:
            #myPrint("wert wird nicht uebernommen")
            return False

    def threadInitMethod(self):
        self.bmsWerte = {}

    def threadMethod(self):
        def takeDataAndSend():
            self.bmsWerte = newMqttMessageDict["content"]
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.bmsWerte, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if not "Vmin" in self.bmsWerte:
                    # if we have to initialise variable
                    takeDataAndSend()
                    # send Values to a homeAutomation to get there sliders sensors selectors and switches
                    self.homeAutomation.mqttDiscoverySensor(self, self.bmsWerte)
                elif self.checkWerteSprung(newMqttMessageDict["content"]["Vmin"], self.bmsWerte["Vmin"], 1, -1, 10):
                    takeDataAndSend()
                elif self.checkWerteSprung(newMqttMessageDict["content"]["Vmax"], self.bmsWerte["Vmax"], 1, -1, 10):
                    takeDataAndSend()
                elif newMqttMessageDict["content"]["BmsEntladeFreigabe"] != self.bmsWerte["BmsEntladeFreigabe"]:
                    takeDataAndSend()
                elif newMqttMessageDict["content"]["toggleIfMsgSeen"] != self.bmsWerte["toggleIfMsgSeen"]:
                    self.bmsWerte = newMqttMessageDict["content"]
                if "Current" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Current"], self.bmsWerte["Current"], 20, -200, 200, 5):
                        takeDataAndSend()
                if "Prozent" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Prozent"], self.bmsWerte["Prozent"], 1, -1, 101):
                        takeDataAndSend()

                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.bmsWerte, globalPublish = False, enableEcho = False)

                if self.timer(name = "timerBasicBmsPublish", timeout = 120):
                    takeDataAndSend()

    def threadBreak(self):
        time.sleep(0.1)