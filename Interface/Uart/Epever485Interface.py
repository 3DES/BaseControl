from Base.InterfaceBase import InterfaceBase
import time
from epevermodbus.driver import EpeverChargeController

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

    def readAndSetParameters(self):

        '''
        • When the battery type is "USE," the battery voltage parameters 
        follow the following logic:
        
        A． Over Voltage Disconnect Voltage > Charging Limit Voltage ≥ 
        Equalize Charging Voltage ≥ Boost Charging Voltage ≥ Float Charging 
        Voltage > Boost Reconnect Charging Voltage.
        B． Over Voltage Disconnect Voltage > Over Voltage Reconnect Voltage
        C． Low Voltage Reconnect Voltage > Low Voltage Disconnect Voltage ≥ 
        Discharging Limit Voltage.
        D． Under Voltage Warning Reconnect Voltage>Under Voltage Warning 
        Voltage≥ Discharging Limit Voltage;
        E． Boost Reconnect Charging voltage >Low Voltage Reconnect Voltage.
        '''
        if self.configuration["floatVoltage"] and self.configuration["boostVoltage"]:
            battery_voltage_control_registers = {
                'over_voltage_disconnect_voltage': self.configuration["boostVoltage"] + 2.0,
                'charging_limit_voltage': self.configuration["boostVoltage"] + 0.5,
                'over_voltage_reconnect_voltage': self.configuration["boostVoltage"] + 0.5,
                'equalize_charging_voltage': self.configuration["boostVoltage"],
                'boost_charging_voltage': self.configuration["boostVoltage"],
                'float_charging_voltage': self.configuration["floatVoltage"],
                'boost_reconnect_charging_voltage': self.configuration["floatVoltage"] - 1.0
            }

            # get actual parameter values, update charge parameters and write it to charge controller
            actual_battery_voltage_control_registers = self.controller.get_battery_voltage_control_registers()
            set_battery_voltage_control_registers ={}
            set_battery_voltage_control_registers.update(actual_battery_voltage_control_registers)
            set_battery_voltage_control_registers.update(battery_voltage_control_registers)
            if actual_battery_voltage_control_registers == set_battery_voltage_control_registers:
                self.logger.info(self, "Epever parameters are already set")
            else:
                self.controller.set_battery_voltage_control_registers_dict(set_battery_voltage_control_registers)

                actual_battery_voltage_control_registers = self.controller.get_battery_voltage_control_registers()
    
                self.logger.info(self, "Epever parameters now set to:")
                for param_name, param_value in actual_battery_voltage_control_registers.items():
                    self.logger.info(self, f"{param_name}: {param_value}")
    
                # todo vergleichen und evtl exception
                if actual_battery_voltage_control_registers == set_battery_voltage_control_registers:
                    self.logger.info(self, "Epever parameters Ok")
                else:
                    raise Exception(f'Device --{self.name}-- Parameters are different to ours')
        else:
            self.logger.info(self, "No Voltage Parameters given!")

    def initEpeverWithRetry(self, retries = maxInitTries):
        tries = 0
        while tries <= retries:
            tries += 1
            try:
                self.controller = EpeverChargeController(self.configuration["interface"], self.configuration["address"])
                break
            except:
                time.sleep(10)
                self.logger.info(self, f"Device --{self.name}-- {tries} from {self.maxInitTries} inits failed.")
                if self.tries >= self.maxInitTries:
                    raise Exception(f'{self.name} connection could not established! Check interface and address')

    def threadInitMethod(self):
        self.tagsIncluded(["interface"])
        self.tagsIncluded(["address"], optional = True, default = 1)
        self.tagsIncluded(["boostVoltage"], optional = True, default = 0)
        self.tagsIncluded(["floatVoltage"], optional = True, default = 0)
        self.initEpeverWithRetry()
        self.readAndSetParameters()

    def threadMethod(self):

        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

            if "cmd" in newMqttMessageDict["content"]:
                if "readState" == newMqttMessageDict["content"]["cmd"]:
                    try:
                        self.chargerValues["PvCurrent"] = self.controller.get_solar_current()
                        self.chargerValues["PvVoltage"] = self.controller.get_solar_voltage()
                        self.chargerValues["Power"] = self.controller.get_solar_power()
                        self.chargerValues["BattVoltage"] = self.controller.get_battery_voltage()
                        self.chargerValues["BattCurrent"] = self.controller.get_battery_current()
                        self.chargerValues["Error"] = self.controller.is_device_over_temperature()
    
                        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), self.chargerValues, globalPublish = False, enableEcho = False)
                        if self.timerExists("ErrorTimer"):
                            self.timer(name = "ErrorTimer", remove = True)
                    except:
                        self.logger.info(self, "Could not read Epever data, try to init again")
                        self.initEpeverWithRetry(10)
                        if self.timer(name = "ErrorTimer", timeout = 100):
                            raise Exception(f'{self.name} Could not read Epever data for more than 100s')

    def threadBreak(self):
        time.sleep(1)