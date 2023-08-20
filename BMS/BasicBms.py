import time
import json
from Base.ThreadObject import ThreadObject
from GPIO.BasicUsbRelais import BasicUsbRelais


class BasicBms(ThreadObject):
    '''
    This class forwards BMS messages to global and notGlobal subscribers. 
    The value have to change in a sensible range/jump to be published globally.
    This class discovers device infos as sensor to a given homeautommation
    
    
    From Bms Interface to this CLass:
    Required:                                   toggleIfMsgSeen
                                                either: keys from interface (>Vmin< >Vmax<) or (>voltagelist<) in combination with parameters vMin, vMax, vMinTimer
                                                or:     key from interface >BmsEntladeFreigabe<

    Optional is                                 FullChargeRequired and BmsLadeFreigabe which is also merged to globalBmsData["merged"]
    Optional is                                 any other value

    From SocMonitor:
    Required:                                   none, upper checks are disabled

    To SocMonitor:
    A content <{"cmd":...}> will be forwarded from inTopic to SocMonitor

    Output at out Topic "not global":
    {"BasicUsbRelais.gpioCmd":{"relBalance": "0"}}
    {"Vmin":3.0, "Vmax":4.0} for

    All bms interface data are merged and will be written to self.globalBmsWerte["merged"]["..."]
    If a voltageList is given vMin and vMax of this list is merged to self.globalBmsWerte["merged"]["Vm.."]
    If parameters are given form init.json the self.globalBmsWerte["merged"] will be checked on "vMin", vMinTimer", "vMax"
    "vMax" rise an exc after 10s
    "vMin" and vMinTimer" sets BmsEntladeFreigabe to False
    "vBal" sets and resets {"BasicUsbRelais.gpioCmd":{"relBalance": "0"}}

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

    def getSocMonitorTopic(self):
        return self.createOutTopic(self.getObjectTopic(self.configuration["socMonitor"]))

    def allDevicesPresent(self):
        return self.numOfDevices == len(list(self.bmsWerte))

    def clearWatchdog(self):
        self.mqttPublish(self.createOutTopic(self.getObjectTopic(), self.MQTT_SUBTOPIC.TRIGGER_WATCHDOG), {"cmd":"clearWdRelay"}, globalPublish = False, enableEcho = False)

    def mergeBmsData(self):
        # this funktion merges all data from all bms interfaces to self.globalBmsWerte["merged"]
        vMinList = []
        vMaxList = []
        entladeFreigabeList = []
        ladeFreigabeList = []
        fullChargeReqList = []
        self.globalBmsWerte["merged"]["Current"] = 0
        self.globalBmsWerte["merged"]["Prozent"] = 0
        divideProzent = 0
        vMinSeen = False
        vMaxSeen = False
        entladefreigabeSeen = False
        ladefreigabeSeen = False
        for topic in list(self.bmsWerte):
            if "Vmin" in self.bmsWerte[topic]:
                vMinList.append(self.bmsWerte[topic]["Vmin"])
                vMinSeen = True
            if "Vmax" in self.bmsWerte[topic]:
                vMaxList.append(self.bmsWerte[topic]["Vmax"])
                vMaxSeen = True
            if "BmsEntladeFreigabe" in self.bmsWerte[topic]:
                entladeFreigabeList.append(self.bmsWerte[topic]["BmsEntladeFreigabe"])
                entladefreigabeSeen = True
            if "Current" in self.bmsWerte[topic]:
                self.globalBmsWerte["merged"]["Current"] += self.bmsWerte[topic]["Current"]
            if "Prozent" in self.bmsWerte[topic]:
                self.globalBmsWerte["merged"]["Prozent"] += self.bmsWerte[topic]["Prozent"]
                divideProzent += 1
            if "VoltageList" in self.bmsWerte[topic]:
                vMinList.append(min(self.bmsWerte[topic]["VoltageList"]))
                vMaxList.append(max(self.bmsWerte[topic]["VoltageList"]))
                vMinSeen = True
                vMaxSeen = True
            if "BmsLadeFreigabe" in self.bmsWerte[topic]:
                ladeFreigabeList.append(self.bmsWerte[topic]["BmsLadeFreigabe"])
                ladefreigabeSeen = True
            if "FullChargeRequired" in self.bmsWerte[topic]:
                fullChargeReqList.append(self.bmsWerte[topic]["FullChargeRequired"])
            if topic != self.configuration["socMonitor"]:
                # check bms data and given parameters
                if not entladefreigabeSeen and not self.tagsIncluded(["vMinTimer","vMax","vMin"]):
                    raise Exception(f"{self.name} Neither entladefreigabe from interface {topic} nor vMin, vMax, vMinTimer in project.json is given.")
                # check bms data either we need vmax and vmin or entladefreigabe
                if not ((vMinSeen and vMaxSeen) or entladefreigabeSeen):
                    raise Exception(f"{self.name} No vMin, vMax or entladefreigabe from interface {topic} seen.")

        if divideProzent:
            self.globalBmsWerte["merged"]["Prozent"] = round(self.globalBmsWerte["merged"]["Prozent"] / divideProzent, 2)
        self.globalBmsWerte["merged"]["Current"] = round(self.globalBmsWerte["merged"]["Current"], 1)
        self.globalBmsWerte["merged"]["Vmin"] = round(min(vMinList), 2)
        self.globalBmsWerte["merged"]["Vmax"] = round(max(vMaxList), 2)

        self.checkAllBmsData()      # to get BmsEntladeFreigabe and BmsLadeFreigabe
        entladeFreigabeList.append(self.globalBmsWerte["calc"]["BmsEntladeFreigabe"])
        ladeFreigabeList.append(self.globalBmsWerte["calc"]["BmsLadeFreigabe"])

        self.globalBmsWerte["merged"]["BmsEntladeFreigabe"] = all(entladeFreigabeList)
        self.globalBmsWerte["merged"]["BmsLadeFreigabe"] = all(ladeFreigabeList)
        if len(fullChargeReqList):
            self.globalBmsWerte["merged"]["FullChargeRequired"] = any(fullChargeReqList)
        if not len(entladeFreigabeList):
            raise Exception("entladeFreigabeList empty")


    def triggerWatchdog(self):
        # this funktion checks all bms toggleSeen bits, this bit was set from threadMethod if interface toggled the bit toggleIfMsgSeen.
        # if toggleSeen bits from all interfaces are set,  we send a trigger msg to given watchdog usb relay and we toggle the output bit toggleIfMsgSeen in self.globalBmsWerte["merged"]

        toggleList = []
        for topic in list(self.bmsWerte):
            if "toggleSeen" in self.bmsWerte[topic]:
                toggleList.append(self.bmsWerte[topic]["toggleSeen"])
            else:
                # add a false to the list if there is no alive info from bms (used for initial state)
                toggleList.append(False)
        if all(toggleList):
            if self.allDevicesPresent():
                self.mqttPublish(self.createOutTopic(self.getObjectTopic(), self.MQTT_SUBTOPIC.TRIGGER_WATCHDOG), {"cmd":"triggerWdRelay"}, globalPublish = False, enableEcho = False)
                # If all neccessary interfaces interfaces toggled their bits we will toggle our own bit too. So following threads can check for a new valid msg.
                self.globalBmsWerte["merged"]["toggleIfMsgSeen"] = not self.globalBmsWerte["merged"]["toggleIfMsgSeen"] 
            # finally we reset all toggleSeen bits for a new cycle
            for topic in list(self.bmsWerte):
                self.bmsWerte[topic]["toggleSeen"] = False

    def updateBalancerRelais(self, value):
        # this function remembers the old relay value and set a new one
        if not "relBalance" in self.globalBmsWerte["calc"]:
            self.globalBmsWerte["calc"]["relBalance"] = "0"
        if value != self.globalBmsWerte["calc"]["relBalance"] and self.allDevicesPresent():
            self.globalBmsWerte["calc"]["relBalance"] = value
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), {BasicUsbRelais.gpioCmd:{"relBalance":str(value)}}, globalPublish = False, enableEcho = False)

    def checkAllBmsData(self):
        # this funktion checks all merged data with given vmin, vmax and timerVmin and writes result to self.globalBmsWerte["calc"]
        # self.globalBmsWerte["merged"]["BmsEntladeFreigabe"] is overwritten if upper check result is false
        # Balancer Relais is also managed here
        if "vMin" in self.configuration["parameters"]:
            if self.globalBmsWerte["merged"]["Vmin"] < self.configuration["parameters"]["vMin"]:
                self.globalBmsWerte["calc"]["VminOk"] = False
                if self.timer(name = "timerVmin", timeout = self.configuration["parameters"]["vMinTimer"]):
                    self.globalBmsWerte["calc"]["BmsEntladeFreigabe"] = False
                    self.clearWatchdog()
                    raise Exception(f"CellVoltage fall below given voltage: {self.configuration['parameters']['vMin']} for {self.configuration['parameters']['vMinTimer']}s.")
            else:
                self.globalBmsWerte["calc"]["VminOk"] = True
                self.globalBmsWerte["calc"]["BmsEntladeFreigabe"] = True
                if self.timerExists("timerVmin"):
                    self.timer(name = "timerVmin",remove = True)

            if self.globalBmsWerte["merged"]["Vmax"] > self.configuration["parameters"]["vMax"]:
                self.globalBmsWerte["calc"]["VmaxOk"] = False 
                if self.timer(name = "timerVmax", timeout = 10):
                    self.globalBmsWerte["calc"]["BmsLadeFreigabe"] = False
                    self.clearWatchdog()
                    raise Exception(f"CellVoltage exceeds given voltage: {self.configuration['parameters']['vMax']} for 10s.")
            else:
                self.globalBmsWerte["calc"]["VmaxOk"] = True
                self.globalBmsWerte["calc"]["BmsLadeFreigabe"] = True
                if self.timerExists("timerVmax"):
                    self.timer(name = "timerVmax",remove = True)

        # now calculate Balancer Relais
        if "vBal" in self.configuration["parameters"]:
            if self.globalBmsWerte["merged"]["Vmax"] > self.configuration["parameters"]["vBal"]:
                self.updateBalancerRelais("1")
            else:
                self.updateBalancerRelais("0")

        self.triggerWatchdog()      # At least if we called mergeBmsData(), checkAllBmsData() we will call triggerWatchdog() to ensure that all merge code was called

    def threadInitMethod(self):
        self.tagsIncluded(["socMonitor"], optional = True)
        self.globalBmsWerte = {"merged":{"toggleIfMsgSeen":False}, "calc":{"BmsEntladeFreigabe":False, "BmsLadeFreigabe":False}}
        self.bmsWerte = {}                                  # local Bms interface data from each interface stored in its topic key
        self.numOfDevices = len(self.interfaceInTopics)
        if self.configuration["socMonitor"] is not None:
            self.mqttSubscribeTopic(self.getSocMonitorTopic(), globalSubscription = False)
            self.numOfDevices += 1

    def threadMethod(self):
        def takeDataAndSendGlobal(interfaceName):
            self.bmsWerte[interfaceName] = newMqttMessageDict["content"]
            self.mergeBmsData()

            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.globalBmsWerte, globalPublish = True, enableEcho = False)
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()) + self.allBmsDataTopicExtension, self.bmsWerte, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            # at first we check which msg is arrived. a socmonitor has prozent and Current
            # A bms has vmin, vmax, BmsEntladeFreigabe, toggleIfMsgSeen and optional prozent and Current
            socMonitorMsg = False
            bmsMsg = False
            toggleSeen = False
            if newMqttMessageDict["topic"] == self.getSocMonitorTopic():
                socMonitorMsg = True
                interfaceName = self.configuration["socMonitor"]
            elif newMqttMessageDict["topic"] in self.interfaceOutTopics:
                bmsMsg = True
                interfaceName = self.getInterfaceNameFromOutTopic(newMqttMessageDict["topic"])
            elif "cmd" in newMqttMessageDict["content"]:
                #  this is a command, we will forward it to the interfaces
                if self.configuration["socMonitor"] is not None:
                    # we will forward it to the soc monitor if it is defined
                    self.mqttPublish(self.createInTopic(self.createProjectTopic(self.configuration["socMonitor"])), newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                for interfaceTopic in self.interfaceInTopics:
                    self.mqttPublish(interfaceTopic, newMqttMessageDict["content"], globalPublish = False, enableEcho = False)

            if bmsMsg or socMonitorMsg:
                if socMonitorMsg:
                    toggleSeen = True                                   # set toggleSeen here, so it has no affect to wdtrigger (face that signal) because a soc monitor dont send this information
                    if not interfaceName in self.bmsWerte:
                        takeDataAndSendGlobal(interfaceName)
                elif bmsMsg:
                    if interfaceName is None:
                        raise Exception("InterfaceName from Bms Interface is None!")
                    # If a new interface sends its msg we will discover it and store data to our local dict
                    if not interfaceName in self.bmsWerte:
                        takeDataAndSendGlobal(interfaceName)
                        # delete soc monitor to prevent double discovery in homeassistant, the soc monitor discovers it self at homeassistant. We mustn't do it.
                        if self.configuration["socMonitor"] in self.bmsWerte:
                            del self.bmsWerte[self.configuration["socMonitor"]]
                        self.homeAutomation.mqttDiscoverySensor(self, self.bmsWerte, topicAd = self.allBmsDataTopicExtension)
                        self.homeAutomation.mqttDiscoverySensor(self, self.globalBmsWerte)
    
                    # At first we check required bit toggleIfMsgSeen. We remember it and add this info at least to bms data of this topic 
                    toggleSeen = (newMqttMessageDict["content"]["toggleIfMsgSeen"] != self.bmsWerte[interfaceName]["toggleIfMsgSeen"])
    
                    # Check optional data, sanity check is done in mergeBmsData()
                    if "Vmin" in newMqttMessageDict["content"]:
                        if self.checkWerteSprung(newMqttMessageDict["content"]["Vmin"], self.bmsWerte[interfaceName]["Vmin"], 1, -1, 10):
                            takeDataAndSendGlobal(interfaceName)
                    if "Vmax" in newMqttMessageDict["content"]:
                        if self.checkWerteSprung(newMqttMessageDict["content"]["Vmax"], self.bmsWerte[interfaceName]["Vmax"], 1, -1, 10):
                            takeDataAndSendGlobal(interfaceName)
                    if "BmsEntladeFreigabe" in newMqttMessageDict["content"]:
                        if newMqttMessageDict["content"]["BmsEntladeFreigabe"] != self.bmsWerte[interfaceName]["BmsEntladeFreigabe"]:
                            takeDataAndSendGlobal(interfaceName)
    
                # Now we check the optional values on its range and hysteresis and publish global
                if "Current" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Current"], self.bmsWerte[interfaceName]["Current"], 20, -200, 200, 5):
                        takeDataAndSendGlobal(interfaceName)
                if "Prozent" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Prozent"], self.bmsWerte[interfaceName]["Prozent"], 1, -1, 101):
                        takeDataAndSendGlobal(interfaceName)

                # if a toggle of toggleIfMsgSeen was seen we remember new value
                if toggleSeen:
                    self.bmsWerte[interfaceName] = newMqttMessageDict["content"]
                # add the toogleSeen value to individual BMS Data
                self.bmsWerte[interfaceName]["toggleSeen"] = toggleSeen

                self.mergeBmsData()

                # now publish merged data to internal threads if all interfaces and SocMonitor has sent data
                if self.allDevicesPresent():
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.globalBmsWerte["merged"], globalPublish = False, enableEcho = False)

                if self.timer(name = "timerBasicBmsPublish", timeout = 120):
                    takeDataAndSendGlobal(interfaceName)

    def threadBreak(self):
        time.sleep(0.6)