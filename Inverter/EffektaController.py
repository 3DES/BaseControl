import time
import datetime
from Base.ThreadBase import ThreadBase


class EffektaController(ThreadBase):
    '''
    classdocs
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
        self.EffektaData["EffektaWerte"] = {"timeStamp": 0, "Netzspannung": 0, "AcOutSpannung": 0, "AcOutPower": 0, "PvPower": 0, "BattCharge": 0, "BattDischarge": 0, "ActualMode": "", "DailyProduction": 0.0, "CompleteProduction": 0, "DailyCharge": 0.0, "DailyDischarge": 0.0, "BattCapacity": 0, "DeviceStatus2": "", "BattSpannung": 0.0}
        self.tempDailyProduction = 0.0
        self.mqttSubscribeTopic(self.createOutTopic(self.getObjectTopic()), globalSubscription = True)

    def threadMethod(self):
        '''
        supported funktions:
        
        if topic includes "queryExtern" or "setValueExtern" we send a extern query or setValue to the interface. The response 
        will be published global. The msg content have to be the name of the parameter in string type.
        
        we send depending of effekta_Query_Cycle a internal query to the interface. If the response arrives we check all values 
        if there are big changes and publish them global.    
        
        we accept our own msg to get our old values initial.
        
        '''

        effekta_Query_Cycle = 20
        # battEnergyCycle = 8
        # timestampbattEnergyCycle = 0
        # tempDailyDischarge = 0.0
        # tempDailyCharge = 0.0

        # possible msg
        # queryTemplate["query"] = {"cmd":"filledfromSender", "response":"filledFromInterface"}
        # setValueTemplate["setValue"] = {"cmd":"filledfromSender", "value":"filledfromSender", "success": filledFromInterface, "extern":filledfromSender}
        self.queryDict["query"] = {"cmd":"", "response":"", "extern":False}
        self.setValueDict["setValue"] = {"cmd":"", "value":"", "success": False, "extern":False}
        
        if self.EffektaData["EffektaWerte"]["timeStamp"] + effekta_Query_Cycle < time.time():
            self.EffektaData["EffektaWerte"]["timeStamp"] = time.time()
            self.queryDict["query"]["extern"] = False
            self.queryDict["query"]["cmd"] = "QPIGS" # Device general status parameters inquiry
            self.mqttPublish(self.interfaceTopics[0], self.queryDict, globalPublish = False, enableEcho = False)
            self.queryDict["query"]["cmd"] = "QMOD" # Device mode parameters inquiry
            self.mqttPublish(self.interfaceTopics[0], self.queryDict, globalPublish = False, enableEcho = False)

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():

            newMqttMessageDict = self.mqttRxQueue.get(block = False)

            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass
            self.sendeGlobalMqtt = False
            
            # First we check if the msg is from extern
            if not (newMqttMessageDict["topic"] in self.interfaceTopics):
                # if the ..Extern is not from interface we will send it to the interface  
                # from extern we only need the sting of parameter
                if "queryExtern" in newMqttMessageDict["topic"]:
                    self.queryDict["query"]["extern"] = True
                    self.queryDict["query"]["cmd"] = newMqttMessageDict["content"]
                    self.mqttPublish(self.interfaceTopics[0], self.queryDict, globalPublish = False, enableEcho = False)
                if "setValueExtern" in newMqttMessageDict["topic"]:
                    self.setValueDict["setValue"]["extern"] = True
                    self.setValueDict["setValue"]["cmd"] = newMqttMessageDict["content"]
                    #self.setValueDict["setValue"]["value"] can be emty. realCmd = cmd concat value
                    self.mqttPublish(self.interfaceTopics[0], self.setValueDict, globalPublish = False, enableEcho = False)                    
            else:
                # The msg is from our interface
                if "EffektaWerte" in newMqttMessageDict["content"]:
                    # if we get our own Data will overwrite internal data. For initial settings like ...Production
                    self.EffektaData = newMqttMessageDict["content"]
                    self.mqttUnSubscribeTopic(self.createOutTopic(self.getObjectTopic()))
                elif "setValue" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["setValue"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict, globalPublish = True, enableEcho = False)                
                elif "query" in newMqttMessageDict["content"]:
                    if newMqttMessageDict["content"]["query"]["extern"]:
                        # if we get a extern msg from our interface we will forward it to the mqtt as global
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), newMqttMessageDict, globalPublish = True, enableEcho = False)
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QMOD" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        if self.EffektaData["EffektaWerte"]["ActualMode"] != newMqttMessageDict["content"]["query"]["response"]:
                            self.sendeGlobalMqtt = True
                            self.EffektaData["EffektaWerte"]["ActualMode"] = newMqttMessageDict["content"]["query"]["response"]
                    elif newMqttMessageDict["content"]["query"]["cmd"] == "QPIGS" and len(newMqttMessageDict["content"]["query"]["response"]) > 0:
                        (Netzspannung, Netzfrequenz, AcOutSpannung, AcOutFrequenz, AcOutPowerVA, AcOutPower, AcOutLoadProz, BusVoltage, BattSpannung, BattCharge, BattCapacity, InverterTemp, PvCurrent, PvVoltage, BattVoltageSCC, BattDischarge, DeviceStatus1, BattOffset, EeVersion, PvPower, DeviceStatus2) = newMqttMessageDict["content"]["query"]["response"].split()
            
                        self.EffektaData["EffektaWerte"]["AcOutSpannung"] = float(AcOutSpannung)
                        
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["Netzspannung"], int(float(Netzspannung)), 3, -1, 10000):
                            self.EffektaData["EffektaWerte"]["Netzspannung"] = int(float(Netzspannung))
                            self.sendeGlobalMqtt = True                
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["AcOutPower"], int(AcOutPower), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["AcOutPower"] = int(AcOutPower)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["PvPower"], int(PvPower), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["PvPower"] = int(PvPower)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattCharge"], int(BattCharge), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattCharge"] = int(BattCharge)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattDischarge"], int(BattDischarge), 10, -1, 10000) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattDischarge"] = int(BattDischarge)
                            self.sendeGlobalMqtt = True
                        if self.EffektaData["EffektaWerte"]["DeviceStatus2"] != DeviceStatus2:
                            self.EffektaData["EffektaWerte"]["DeviceStatus2"] = DeviceStatus2
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattSpannung"], float(BattSpannung), 0.5, -1, 100) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattSpannung"] = float(BattSpannung)
                            self.sendeGlobalMqtt = True
                        if self.checkWerteSprung(self.EffektaData["EffektaWerte"]["BattCapacity"], int(BattCapacity), 1, -1, 101) or self.sendeGlobalMqtt:
                            self.EffektaData["EffektaWerte"]["BattCapacity"] = int(BattCapacity)
                            self.sendeGlobalMqtt = True
                            
                        self.tempDailyProduction = self.tempDailyProduction + (int(PvPower) * effekta_Query_Cycle / 60 / 60 / 1000)
                        self.EffektaData["EffektaWerte"]["DailyProduction"] = round(self.tempDailyProduction, 2)
                        
                        if self.sendeGlobalMqtt:
                            self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData, globalPublish = True, enableEcho = False)
                        else:
                            pass
                            # @todo send aktual values here
                            #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData, globalPublish = False, enableEcho = False)

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
         
                    # reset response for next cycle


        now = datetime.datetime.now()
        if now.hour == 23:
            if self.EffektaData["EffektaWerte"]["DailyProduction"] > 0.0:
                self.EffektaData["EffektaWerte"]["CompleteProduction"] = self.EffektaData["EffektaWerte"]["CompleteProduction"] + round(self.EffektaData["EffektaWerte"]["DailyProduction"])
                self.EffektaData["EffektaWerte"]["DailyProduction"] = 0.0
                self.tempDailyProduction = 0.0
            #self.EffektaData["EffektaWerte"]["DailyDischarge"] = 0.0
            #tempDailyDischarge = 0.0
            #self.EffektaData["EffektaWerte"]["DailyCharge"] = 0.0
            #tempDailyCharge = 0.0
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.EffektaData, globalPublish = True, enableEcho = False)