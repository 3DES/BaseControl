from Base.InterfaceBase import InterfaceBase
import time
from epevermodbus.driver import EpeverChargeController
import json

class Epever485Interface(InterfaceBase):
    '''
    classdocs
    '''
    
    maxInitTries = 10

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.chargerValues = {"PvCurrent":0.0, "PvVoltage":0.0, "Power":0.0, "BattVoltage":0.0, "BattCurrent":0.0, "Error":False}

    def threadInitMethod(self):
        self.tagsIncluded(["interface", "address"])
        self.tries = 0
        while self.tries <= self.maxInitTries:
            self.tries += 1
            try:
                self.controller = EpeverChargeController(self.configuration["interface"], self.configuration["address"])
                break
            except:
                time.sleep(10)
                self.logger.info(self, f"Device --{self.name}-- {self.tries} from {self.maxInitTries} inits failed.")
                if self.tries >= self.maxInitTries:
                    raise Exception(f'{self.name} connection could not established! Check interface and address')

    def threadMethod(self):

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)
            try:
                newMqttMessageDict["content"] = json.loads(newMqttMessageDict["content"])      # try to convert content in dict
            except:
                pass

            if "cmd" in newMqttMessageDict["content"]:
                if "readState" == newMqttMessageDict["content"]["cmd"]:
                    self.chargerValues["PvCurrent"] = self.controller.get_solar_current()
                    self.chargerValues["PvVoltage"] = self.controller.get_solar_voltage()
                    self.chargerValues["Power"] = self.controller.get_solar_power()
                    self.chargerValues["BattVoltage"] = self.controller.get_battery_voltage()
                    self.chargerValues["BattCurrent"] = self.controller.get_battery_current()
                    self.chargerValues["Error"] = self.controller.is_device_over_temperature()

                    self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = False, enableEcho = False)

    def threadBreak(self):
        time.sleep(0.5)