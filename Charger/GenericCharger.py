import time
import json
from Base.ThreadObject import ThreadObject
import datetime


class GenericCharger(ThreadObject):
    '''
    This class forwards Charger messages to global and noGlobal subscribers. 
    The value have to change in a sensible range/jump to be published globally.
    This class discovers device infos as sensor to a given homeautommation
    This class needs key Power in a dict from given Charger interface.
    Optional is PvCurrent and PvVoltage which will be also checked for sensible range/jump.
    Optional is any other Value.
    CompleteProduction and DailyProduction is calculatet
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
        self.chargerValues = {"CompleteProduction": 0.0, "DailyProduction": 0.0}
        #subscribe to get old data from mqtt
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        self.query_Cycle = 20
        self.tempDailyProduction = 0.0

    def threadMethod(self):
        def takeDataAndSend():
            self.chargerValues.update(newMqttMessageDict["content"])
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if not "Power" in self.chargerValues:
                    # if we have to initialise variable
                    takeDataAndSend()
                    # send Values to a homeAutomation to get there sliders sensors selectors and switches
                    self.homeAutomation.mqttDiscoverySensor(self, self.chargerValues)
                elif self.checkWerteSprung(newMqttMessageDict["content"]["Power"], self.chargerValues["Power"], 10, -1, 10000):
                    takeDataAndSend()

                # optional Values
                if "PvVoltage" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["PvVoltage"], self.chargerValues["PvVoltage"], 10, -1, 200):
                        takeDataAndSend()
                if "PvCurrent" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["PvCurrent"], self.chargerValues["PvCurrent"], 20, -1, 200, 5):
                        takeDataAndSend()

                # Publish internally
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = False, enableEcho = False)

                self.tempDailyProduction = self.tempDailyProduction + (int(self.chargerValues["Power"]) * self.query_Cycle / 60 / 60 / 1000)
                self.chargerValues["DailyProduction"] = round(self.tempDailyProduction, 2)

                # We publish every 120s
                if self.timer(name = "timerChargerPublish", timeout = 120):
                    takeDataAndSend()
            else:
                if "CompleteProduction" in newMqttMessageDict["content"]:
                    # if we get our own Data will overwrite internal data. For initial settings like ...Production
                    self.chargerValues["CompleteProduction"] = newMqttMessageDict["content"]["CompleteProduction"]
                    self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))


        now = datetime.datetime.now()
        if now.hour == 23:
            if self.chargerValues["DailyProduction"] > 0.0:
                self.chargerValues["CompleteProduction"] = self.chargerValues["CompleteProduction"] + round(self.chargerValues["DailyProduction"])
                self.chargerValues["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
                self.sendeGlobalMqtt = True

        if self.timer(name = "timerChargerStateReq", timeout = self.query_Cycle, firstTimeTrue = True):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readState"}, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(0.3)
