import time
import json
from Base.ThreadObject import ThreadObject
from GPIO.BasicUsbRelais import BasicUsbRelais


class BasicBms(ThreadObject):
    '''
    This class forwards BMS messages to global and noGlobal subscribers. 
    The value have to change in a sensible range/jump to be published globally.
    This class discovers device infos as sensor to a given homeautommation
    This class needs key Vmin, Vmax, BmsEntladeFreigabe and toggleIfMsgSeen in a dict from given BMS interface.
    Optional is a key named VoltageList which is merged to globalBmsData["merged"]
    Optional is FullChargeRequired and BmsLadeFreigabe which is also merged to globalBmsData["merged"]

    If parameters are given form init.json then the self.globalBmsWerte["calc"] data are internally published, else self.globalBmsWerte["merged"] 
    All bms are merged together and were written to self.globalBmsWerte["merged"]["..."]
    If VoltageList is given it will be iterated and min and max value is written to self.globalBmsWerte["merged"]["Vm.."]
    If parameters are given form init.json the self.globalBmsWerte["merged"] will be checked on "vMin", vMinTimer", "vMax"
    "vMax" rise an exc after 10s, "vMin" and vMinTimer" sets BmsEntladeFreigabe to False, "vBal" sets and resets {"BasicUsbRelais.gpioCmd":{"relBalance": "0"}}

    Optional is Current and Prozent which will be also checked for sensible range/jump.
    Optional is any other Value.
    A global publish is also triggert every 120 seconds
    '''

    allBmsDataTopicExtension = "/allData"

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["parameters"], optional = True, default = {})


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

    def mergeBmsData(self):
        # this fnktion merges all data from all bms interfaces to self.globalBmsWerte["merged"]
        vMinList = []
        vMaxList = []
        entladeFreigabeList = []
        ladeFreigabeList = []
        fullChargeReqList = []
        self.globalBmsWerte["merged"]["Current"] = 0
        self.globalBmsWerte["merged"]["Prozent"] = 0
        divideProzent = 0
        for topic in list(self.bmsWerte):
            vMinList.append(self.bmsWerte[topic]["Vmin"])
            vMaxList.append(self.bmsWerte[topic]["Vmax"])
            entladeFreigabeList.append(self.bmsWerte[topic]["BmsEntladeFreigabe"])
            # now optional values
            if "Current" in self.bmsWerte[topic]:
                self.globalBmsWerte["merged"]["Current"] += self.bmsWerte[topic]["Current"]
                divideProzent += 1
            if "Prozent" in self.bmsWerte[topic]:
                self.globalBmsWerte["merged"]["Prozent"] += self.bmsWerte[topic]["Prozent"]
            if "VoltageList" in self.bmsWerte[topic]:
                self.globalBmsWerte["calc"]["Vmin"] = min(self.bmsWerte[topic]["VoltageList"])
                vMinList.append(self.globalBmsWerte["calc"]["Vmin"])
                self.globalBmsWerte["calc"]["Vmax"] = max(self.bmsWerte[topic]["VoltageList"])
                vMaxList.append(self.globalBmsWerte["calc"]["Vmax"])
            if "BmsLadeFreigabe" in self.bmsWerte[topic]:
                ladeFreigabeList.append(self.bmsWerte[topic]["BmsLadeFreigabe"])
            if "FullChargeRequired" in self.bmsWerte[topic]:
                fullChargeReqList.append(self.bmsWerte[topic]["FullChargeRequired"])

        if divideProzent:
            self.globalBmsWerte["merged"]["Prozent"] /= divideProzent
        if not len(entladeFreigabeList):
            raise Exception("entladeFreigabeList empty")
        self.globalBmsWerte["merged"]["Vmin"] = min(vMinList)
        self.globalBmsWerte["merged"]["Vmax"] = max(vMaxList)
        self.globalBmsWerte["merged"]["BmsEntladeFreigabe"] = all(entladeFreigabeList)
        if len(ladeFreigabeList):
            self.globalBmsWerte["merged"]["BmsLadeFreigabe"] = all(ladeFreigabeList)
        if len(fullChargeReqList):
            self.globalBmsWerte["merged"]["FullChargeRequired"] = any(fullChargeReqList)


    def triggerWatchdog(self):
        # this funktion checks all bms toggleSeen bits, this bit was set from threadMethod if interface toggled the bit toggleIfMsgSeen.
        # if toggleSeen bits from all interfaces are set,  we send a trigger msg to given watchdog usb relay and we toggle the output bit toggleIfMsgSeen in self.globalBmsWerte["merged"]
        # at least we reset all toggle seen bits for a new cycle
        toggleList = []
        for topic in list(self.bmsWerte):
            try:
                toggleList.append(self.bmsWerte[topic]["toggleSeen"])
            except:
                # add a false to the list if there is no alive info from bms (used for initial state)
                toggleList.append(False)
                self.globalBmsWerte["merged"]["toggleIfMsgSeen"] = False
        if all(toggleList):
            self.mqttPublish(self.createOutTopic(self.getObjectTopic(), self.MQTT_SUBTOPIC.TRIGGER_WATCHDOG), {"cmd":"triggerWdRelay"}, globalPublish = False, enableEcho = False)
            for topic in list(self.bmsWerte):
                self.bmsWerte[topic]["toggleSeen"] = False
            try:
                self.globalBmsWerte["merged"]["toggleIfMsgSeen"] = not self.globalBmsWerte["merged"]["toggleIfMsgSeen"] 
            except:
                self.globalBmsWerte["merged"]["toggleIfMsgSeen"] = True

    def updateBalancerRelais(self, value):
        # this funktion remembers the old relay value and set a new one
        if value != self.globalBmsWerte["calc"]["Balancer"]:
            self.globalBmsWerte["calc"]["Balancer"] = value
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {BasicUsbRelais.gpioCmd:{"relBalance":str(value)}}, globalPublish = False, enableEcho = False) # todo testen siehe letzter commit in dieser Zeile

    def checkAllBmsData(self):
        # this funktion checks all merged data with given vmin, vmax and timerVmin and writes result to self.globalBmsWerte["calc"]
        # self.globalBmsWerte["merged"]["BmsEntladeFreigabe"] is overwritten if upper check result is false
        # Balancer Relais is also managed here
        if "vMin" in self.configuration["parameters"]:
            if not "BmsEntladeFreigabe" in self.globalBmsWerte["calc"]:
                self.globalBmsWerte["calc"]["BmsEntladeFreigabe"] = False
            if self.globalBmsWerte["merged"]["Vmin"] < self.configuration["parameters"]["vMin"]:
                self.globalBmsWerte["calc"]["VminOk"] = False
                if self.timer(name = "timerVmin", timeout = self.configuration["parameters"]["vMinTimer"]):
                    self.globalBmsWerte["calc"]["BmsEntladeFreigabe"] = False
            else:
                self.globalBmsWerte["calc"]["VminOk"] = True
                self.globalBmsWerte["calc"]["BmsEntladeFreigabe"] = True
                if self.timerExists("timerVmin"):
                    self.timer(name = "timerVmin",remove = True)

            if self.globalBmsWerte["merged"]["Vmax"] > self.configuration["parameters"]["vMax"]:
                self.globalBmsWerte["calc"]["VmaxOk"] = False 
                if self.timer(name = "timerVmax", timeout = 10):
                    raise Exception("CellVoltage exceeds given maximum for 10s.")
            else:
                if self.timerExists("timerVmax"):
                    self.timer(name = "timerVmax",remove = True)
                self.globalBmsWerte["calc"]["VmaxOk"] = True
            # If calculated value from BasicBms Class is false, we will set merged data also to false
            if not self.globalBmsWerte["calc"]["BmsEntladeFreigabe"]:
                self.globalBmsWerte["merged"]["BmsEntladeFreigabe"] = False

        # now calculate Balancer Relais
        if "vBal" in self.configuration["parameters"]:
            if not "Balancer" in self.globalBmsWerte["calc"]:
                self.globalBmsWerte["calc"]["Balancer"] = "0"
            if self.globalBmsWerte["merged"]["Vmax"] > self.configuration["parameters"]["vBal"]:
                self.updateBalancerRelais("1")
            else:
                self.updateBalancerRelais("0")

    def threadInitMethod(self):
        self.globalBmsWerte = {"merged":{}, "calc":{}}
        self.bmsWerte = {}

    def threadMethod(self):
        def takeDataAndSend():
            interfaceName = self.getInterfaceNameFromOutTopic(newMqttMessageDict["topic"])
            self.bmsWerte[interfaceName] = newMqttMessageDict["content"]
            self.mergeBmsData()
            self.checkAllBmsData()

            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.globalBmsWerte, globalPublish = True, enableEcho = False)
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + self.allBmsDataTopicExtension, self.bmsWerte, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                interfaceName = self.getInterfaceNameFromOutTopic(newMqttMessageDict["topic"])
                if interfaceName is None:
                    raise Exception("InterfaceName from Bms Interface is None!")
                if not interfaceName in self.bmsWerte:
                    takeDataAndSend()
                    self.homeAutomation.mqttDiscoverySensor(self, self.bmsWerte, topicAd = self.allBmsDataTopicExtension)
                    self.homeAutomation.mqttDiscoverySensor(self, self.globalBmsWerte)

                # At first we check if the bit toggleIfMsgSeen was toggelt. We remember it and add this info at least to bms data of this topic 
                toggleSeen = False
                if newMqttMessageDict["content"]["toggleIfMsgSeen"] != self.bmsWerte[interfaceName]["toggleIfMsgSeen"]:
                    toggleSeen = True
                # Now we check the recommendded values on its range and hysteresis and publish global
                if self.checkWerteSprung(newMqttMessageDict["content"]["Vmin"], self.bmsWerte[interfaceName]["Vmin"], 1, -1, 10):
                    takeDataAndSend()
                elif self.checkWerteSprung(newMqttMessageDict["content"]["Vmax"], self.bmsWerte[interfaceName]["Vmax"], 1, -1, 10):
                    takeDataAndSend()
                elif newMqttMessageDict["content"]["BmsEntladeFreigabe"] != self.bmsWerte[interfaceName]["BmsEntladeFreigabe"]:
                    takeDataAndSend()
                # Now we check the optional values on its range and hysteresis and publish global
                if "Current" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Current"], self.bmsWerte[interfaceName]["Current"], 20, -200, 200, 5):
                        takeDataAndSend()
                if "Prozent" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Prozent"], self.bmsWerte[interfaceName]["Prozent"], 1, -1, 101):
                        takeDataAndSend()

                # if a toggle of toggleIfMsgSeen was seen we remember new value
                if toggleSeen:
                    self.bmsWerte[interfaceName] = newMqttMessageDict["content"]
                # add the toogleSeen value to individual BMS Data
                self.bmsWerte[interfaceName]["toggleSeen"] = toggleSeen

                self.mergeBmsData()
                self.checkAllBmsData()
                self.triggerWatchdog()

                # todo, es kann sein, dass sich initial nicht alle bms gemeldet haben, der wd wird dann trotzdem getriggert wird.

                # now publish merged data to internal threads
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.globalBmsWerte["merged"], globalPublish = False, enableEcho = False)

                if self.timer(name = "timerBasicBmsPublish", timeout = 120):
                    takeDataAndSend()

    def threadBreak(self):
        time.sleep(0.6)