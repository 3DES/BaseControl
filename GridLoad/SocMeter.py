import time
import datetime
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter


class SocMeter(ThreadObject):
    '''
    This class checks values from its interface and publishes globally if sensible range/jump is high enough
    
    Initially this class subscribes to its own out topic to get old SOC value back from mqtt. It will be forwarded to interface with e.g. this msg {"cmd":["setSocToValue", "90"]}, where the 90 here is the received percentage value
    If a msg is received from own out topic the class unsubscribes it from its own out topic.
    
    A msg received at the in topic like {"cmd":...} will be forwarded to the interface
     
    '''
    InitAkkuProz = -1

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor

        set SOC Value:    mosquitto_pub -h localhost -p 1883  -u xxx -P xxx -t "HomeAccu/SocMonitor/in" -m "{\"Prozent\":79}"
        '''
        super().__init__(threadName, configuration)


    # thread is not yet ready just because initialization has been done since thread should wait until first SOC message has arrived from interface, so overwrite setThreadStarted() and set the variable manually later on
    def setThreadStarted(self):
        pass


    def threadInitMethod(self):
        self.SocMonitorWerte = { "Ah" : -1, "Current" : 0, "Prozent" : self.InitAkkuProz}

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self.SocMonitorWerte)
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)

        # subscribe global to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)


    def threadMethod(self):

        def takeDataAndSend():
            self.SocMonitorWerte.update(newMqttMessageDict["content"])
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = True, enableEcho = False)
            # @todo remove!! Workaround damit der Strom auf der PV Anzeige richtig angezeigt wird
            temp = {}
            temp["AkkuStrom"] = self.SocMonitorWerte["Current"]
            temp["AkkuProz"] = self.SocMonitorWerte["Prozent"]
            # todo initial timeout
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + "/PvAnzeige", temp, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            # check if msg is from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                self.threadStarted = True       # first message from interface has been received so initalization is done now, therefore, set variable to True
                if "Current" in newMqttMessageDict["content"]:
                    if Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Current"], self.SocMonitorWerte["Current"], -200, 200, percent = 20, dynamic = True, minIgnoreDelta = 5):
                        takeDataAndSend()
                    elif Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Prozent"], self.SocMonitorWerte["Prozent"], -1, 101, percent = 1, dynamic = True):
                        takeDataAndSend()
                    elif Supporter.deltaOutsideRange(newMqttMessageDict["content"]["Ah"], self.SocMonitorWerte["Ah"], -1, 500, percent = 1, dynamic = True, minIgnoreDelta = 10):
                        takeDataAndSend()
                    # send always locally
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


    def threadBreak(self):
        time.sleep(.2)
