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
    WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME = "preWaitingForRetainedSocValue"
    WAITING_FOR_RETAINED_SOC_VALUE_POST_TIMER_NAME = "postWaitingForRetainedSocValue"


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor

        set SOC Value:    mosquitto_pub -h localhost -p 1883  -u xxx -P xxx -t "HomeAccu/SocMonitor/in" -m "{\"Prozent\":79}"
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded("preferRetainedSoc", optional = True, default = False)


    # thread is not yet ready just because initialization has been done since thread should wait until first SOC message has arrived from interface, so overwrite setThreadStarted() and set the variable manually later on
    def setThreadStarted(self):
        pass


    # check if MQTT precentage messages are accepted or to be ignored
    # returns True when the pre timer still exists and hasn't expired so far, otherwise it removes the pre timer and returns False from now on 
    def acceptMqttPercentageValue(self):
        # accept Mqtt messages when pre timer is still running
        if self.timerExists(self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME):
            if not self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME):
                return True
            else:
                self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME, remove = True)
        return False


    # check if SOC messages are accepted or to be ignored
    def acceptSocMessages(self):
        # ignore SOC messages when pre timer is still running
        if self.timerExists(self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME):
            return False
        # also ignore SOC messages when post timer is still running
        if self.timerExists(self.WAITING_FOR_RETAINED_SOC_VALUE_POST_TIMER_NAME):
            if not self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_POST_TIMER_NAME):
                return False
            else:
                self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_POST_TIMER_NAME, remove = True)
        return True


    # set SOC percentage value to given value 
    def setSocPercentValue(self, newValue : int):
        publishMessage = {"cmd":["setSocToValue", str(int(newValue))]}
        self.mqttPublish(self.interfaceInTopics[0], publishMessage, globalPublish = False, enableEcho = False)

        # pre timer no longer needed
        if self.timerExists(self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME):
            self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME, remove = True)

        # new value forced, so ensure 
        self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_POST_TIMER_NAME, timeout = 10, oneShot = True)


    def threadInitMethod(self):
        self.SocMonitorWerte = { "Ah" : -1, "Current" : 0, "Prozent" : self.InitAkkuProz}

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self.SocMonitorWerte)
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)

        # subscribe global to own out topic to get old data and set timeout
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)

        if "forceSoc" in self.configuration:
            forceValue = self.configuration["forceSoc"]
            self.logger.warning(self, f"SOC value forced to {forceValue}, please remove json entry \"forceSoc\"")
            Supporter.debugPrint(f"SOC value forced to {forceValue}, please remove json entry \"forceSoc\"", color = "RED")
            self.setSocPercentValue(forceValue)
        elif self.configuration["preferRetainedSoc"]:
            # wait for retained message from MQTT broker
            self.timer(name = self.WAITING_FOR_RETAINED_SOC_VALUE_PRE_TIMER_NAME, timeout = 60, oneShot = True)


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

            if "cmd" in newMqttMessageDict["content"]:
                # always accept commands
                self.mqttPublish(self.interfaceInTopics[0], {"cmd":str(newMqttMessageDict["content"]["cmd"])}, globalPublish = False, enableEcho = False)
            else:
                if self.acceptMqttPercentageValue():
                    if "Prozent" in newMqttMessageDict["content"] and newMqttMessageDict["global"]:

                        # If we receive a global msg with a Prozent key we will forward it to the interface with the cmd setSocValue to set the value
                        self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
                        if (self.SocMonitorWerte["Prozent"] != self.InitAkkuProz):
                            raise Exception("This situation should not happen, if we are waiting for MQTT messages the Prozent value should still contain init value")

                        # set received value as SOC percentage value
                        self.setSocPercentValue(newMqttMessageDict["content"]["Prozent"])
                elif self.acceptSocMessages():
                    # accept SOC messages but ignore non-command Mqtt messages
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
