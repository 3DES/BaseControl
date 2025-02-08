import time
from Base.ThreadObject import ThreadObject
import datetime
from Base.Supporter import Supporter


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

    def threadInitMethod(self):
        self.chargerValues = {"CompleteProduction": 0.0, "DailyProduction": 0.0}
        # subscribe to own out topic get old data from mqtt
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)
        self.query_Cycle = 20
        self.tempDailyProduction = 0.0
        self.initialMqttTimeout = False

    def threadMethod(self):
        def takeDataAndSend():
            self.chargerValues.update(newMqttMessageDict["content"])
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = True, enableEcho = False)

        if (not self.initialMqttTimeout) and self.timer(name = "timerInitialMqttTimeout", timeout = 60, removeOnTimeout = True):
            self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
            self.initialMqttTimeout = True

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if self.initialMqttTimeout:
                    if not "Power" in self.chargerValues:
                        # if we have to initialise variable
                        takeDataAndSend()
                        # send Values to a homeAutomation to get there sliders sensors selectors and switches
                        self.homeAutomation.mqttDiscoverySensor(self.chargerValues)
                    elif Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Power"], self.chargerValues["Power"], -1, 10000, percent = 10, dynamic = True):
                        takeDataAndSend()

                    # optional Values
                    if "PvVoltage" in newMqttMessageDict["content"]:
                        if Supporter.deltaOutsideRange(newMqttMessageDict["content"]["PvVoltage"], self.chargerValues["PvVoltage"], -1, 200, percent = 10, dynamic = True):
                            takeDataAndSend()
                    if "PvCurrent" in newMqttMessageDict["content"]:
                        if Supporter.deltaOutsideRange(newMqttMessageDict["content"]["PvCurrent"], self.chargerValues["PvCurrent"], -1, 200, percent = 20, dynamic = True, minIgnoreDelta = 5):
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
                    self.initialMqttTimeout = True


        now = datetime.datetime.now()
        if now.hour == 23:
            if self.chargerValues["DailyProduction"] > 0.0:
                self.chargerValues["CompleteProduction"] = self.chargerValues["CompleteProduction"] + round(self.chargerValues["DailyProduction"])
                self.chargerValues["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
                self.sendeGlobalMqtt = True

        if self.initialMqttTimeout and self.timer(name = "timerChargerStateReq", timeout = self.query_Cycle, firstTimeTrue = True):
            self.mqttPublish(self.interfaceInTopics[0], {"cmd":"readState"}, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(5)
