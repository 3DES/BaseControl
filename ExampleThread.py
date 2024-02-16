import time
import datetime
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter


class ExampleThread(ThreadObject):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

    def threadInitMethod(self):
        # subscribe to own in topic if external values are expected
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)

        # discover home automation stuff here!
        #self.exampleThreadValues = { "Ah" : -1, "Current" : 0, "Percent" : 99}
        #homeAutomationUnits = { "Ah" : "Ah"}
        #self.homeAutomation.mqttDiscoverySensor(self.exampleThreadValues, unitDict = homeAutomationUnits, subTopic = "homeautomation")

        # subscribe globally to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            # check if msg is from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if "Current" in newMqttMessageDict["content"]:
                    if Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Current"], self.SocMonitorWerte["Current"], -200, 200, percent = 20, dynamic = True, minIgnoreDelta = 5):
                        takeDataAndSend()
                    elif Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Prozent"], self.SocMonitorWerte["Prozent"], -1, 101, percent = 1, dynamic = True):
                        takeDataAndSend()
                    elif Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Ah"], self.SocMonitorWerte["Ah"], -1, 500, percent = 1, dynamic = True, minIgnoreDelta = 10):
                        takeDataAndSend()
                    # send always localy
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
            else:
                if "cmd" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], {"cmd":str(newMqttMessageDict["content"]["cmd"])}, globalPublish = False, enableEcho = False)
                elif "Prozent" in newMqttMessageDict["content"] and newMqttMessageDict["global"]:
                    # If we receive a global msg with a Prozent key we will forward it to the interface with the cmd setSocValue to set the value
                    self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
                    if self.SocMonitorWerte["Prozent"] != self.InitAkkuProz:
                        self.mqttPublish(self.interfaceInTopics[0], {"cmd":["setSocToValue", str(int(newMqttMessageDict["content"]["Prozent"]))]}, globalPublish = False, enableEcho = False)


                    # @todo -> soc monitor
                    #if len(EffekaQPIGS) > 0:
                    #    if timestampbattEnergyCycle + battEnergyCycle < time.time():
                    #        timestampbattEnergyCycle = time.time()
                    #        if SocMonitorWerte["Currentaktuell"] > 0:
                    #            tempDailyCharge = tempDailyCharge  + ((float(BattSpannung) * SocMonitorWerte["Currentaktuell"]) * battEnergyCycle / 60 / 60 / 1000)
                    #            self.EffektaData["EffektaWerte"]["DailyCharge"] = round(tempDailyCharge, 2)         
                    #        elif SocMonitorWerte["Currentaktuell"] < 0:
                    #            tempDailyDischarge = tempDailyDischarge  + ((float(BattSpannung) * abs(SocMonitorWerte["Currentaktuell"])) * battEnergyCycle / 60 / 60 / 1000)
                    #            self.EffektaData["EffektaWerte"]["DailyDischarge"] = round(tempDailyDischarge, 2)
