import time
import datetime
import json
from Base.ThreadObject import ThreadObject


class SocMeter(ThreadObject):
    '''
    classdocs
    '''
    InitAkkuProz = -1

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
        self.SocMonitorWerte = { "Ah":-1, "Current":0, "Prozent": self.InitAkkuProz}
        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomation.mqttDiscoverySensor(self, self.SocMonitorWerte)

    def threadMethod(self):

        def takeDataAndSend():
            self.SocMonitorWerte.update(newMqttMessageDict["content"])
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.SocMonitorWerte, globalPublish = True, enableEcho = False)
            # @todo remove!! Workaround damit der Strom auf der PV Anzeige richtig angezeigt wird
            temp = {}
            temp["AkkuStrom"] = self.SocMonitorWerte["Current"]
            temp["AkkuProz"] = self.SocMonitorWerte["Prozent"]
            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), temp, globalPublish = True, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            # check if msg is from our interface
            if (newMqttMessageDict["topic"] in self.interfaceOutTopics):
                if "Current" in newMqttMessageDict["content"]:
                    if self.checkWerteSprung(newMqttMessageDict["content"]["Current"], self.SocMonitorWerte["Current"], 20, -200, 200, 5):
                        takeDataAndSend()
                    elif self.checkWerteSprung(newMqttMessageDict["content"]["Prozent"], self.SocMonitorWerte["Prozent"], 1, -1, 101):
                        takeDataAndSend()
                    elif self.checkWerteSprung(newMqttMessageDict["content"]["Ah"], self.SocMonitorWerte["Ah"], 1, -1, 500, 10):
                        takeDataAndSend()
                    # send always localy
                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
            else:
                if "cmd" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], newMqttMessageDict["content"], globalPublish = False, enableEcho = False)
                elif "resetSoc" in newMqttMessageDict["content"]:
                    self.mqttPublish(self.interfaceInTopics[0], {"cmd":"socResetMaxAndHold"}, globalPublish = False, enableEcho = False)
                    # Wir schreiben gleich 100 in den Akkustand um einen fehlerhaften Schaltvorgang aufgrund des aktuellen Akkustandes zu verhindern
                    self.SocMonitorWerte["Prozent"] = 100 


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
