import json

from HomeAutomation.BaseHomeAutomation import BaseHomeAutomation
from Base.ThreadObject import ThreadObject


class HomeAssistantDiscover(BaseHomeAutomation):
    '''
    classdocs
    '''

    @classmethod
    def _getFrindlyName(cls, deviceName, valueName):
        return deviceName + " " + valueName

    @classmethod
    def _getValueTemplateInt(cls, name):
        return r"{{ value_json.%s | int }}" %name

    @classmethod
    def _getValueTemplateNonInt(cls, name):
        return r"{{ value_json.%s }}" %name

    @classmethod
    def _getCmdTemplate(cls, name):
        return r'{"%s": {{ value }} }' %name

    @classmethod
    def _getPayloadOn(cls, name):
        return r'{"%s" : true}' %name

    @classmethod
    def _getPayloadOff(cls, name):
        return r'{"%s" : false}' %name

    @classmethod
    def _getUnitOfMeasurement(cls, valueName):
        units = {"W":["power"], "A":["curr", "battdischarge", "battcharge"], "KWh":["daily", "produ"], "V":["spannung", "voltage"], "%":["prozent"]}
        for unit in units:
            if valueName.lower() in units[unit]:
                return unit
        return ""

    @classmethod
    def getDiscoverySensorTopic(cls, deviceName, sensorName):
        return f"homeassistant/sensor/{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoverySensorCmd(cls, deviceName, sensorName, niceName, unit):
        """
        https://www.home-assistant.io/docs/mqtt/discovery/
        topic "homeassistant/sensor/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/binary_sensor/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein nameDict angegeben ist dann wird der devicName + KeyName als frindlyName verwendet
        Wenn kein unitDict angegeben ist dann wird versucht die Einheit aus dem Keyname abzuleiten
        deviceName: wird zu bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        dataNames: dict oder list. Bei einem dict werden nur die keys verwendet
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        unitDict: dict. hier koennen einzelne key mit der jeweiligen Einheit drin stehen.
        """
        templateMsg = {"state_topic":"", "name": "", "value_template":"", "unit_of_measurement":""}

        templateMsg["state_topic"] = ThreadObject.createOutTopic(ThreadObject.createProjectTopic(deviceName))
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        if len(unit):
            templateMsg["unit_of_measurement"] = unit
        else:
            templateMsg["unit_of_measurement"] = cls._getUnitOfMeasurement(unit)
        # we assume that every value with unit is a int or float, and we have to use _getValueTemplateInt()
        if len(templateMsg["unit_of_measurement"]):
            templateMsg["value_template"] = cls._getValueTemplateInt(sensorName)
        else:
            templateMsg["value_template"] = cls._getValueTemplateNonInt(sensorName)

        return templateMsg


    @classmethod
    def getDiscoverySelectorTopic(cls, deviceName, sensorName):
        return f"homeassistant/select/{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoverySelectorCmd(cls,  deviceName, optionList, niceName = ""):
        """
        https://www.home-assistant.io/docs/mqtt/discovery/
        topic "homeassistant/switch/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/switch/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein nameDict angegeben ist dann wird der devicName + KeyName als frindlyName verwendet
        deviceName: wird zu bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        dataNames: dict oder list. Bei einem dict werden nur die keys verwendet
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        """
        templateMsg = {"command_topic":"", "name": "", "options":[]}
        #templateMsg = {"command_topic":"", "name": "", "options":[], "command_template":""}

        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        if len(niceName):
            templateMsg["name"] = niceName
            #templateMsg["command_template"] = cls._getCmdTemplate(niceName)
        else:
            templateMsg["name"] = deviceName
            #templateMsg["command_template"] = cls._getCmdTemplate(deviceName)
        templateMsg["options"] = optionList
        return templateMsg


    @classmethod
    def getDiscoveryInputNumberSliderTopic(cls, deviceName, sensorName):
        return f"homeassistant/number/{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoveryInputNumberSliderCmd(cls,  deviceName, sensorName, niceName = "", minVal = 0, maxVal = 100):
        """
        https://www.home-assistant.io/docs/mqtt/discovery/
        topic "homeassistant/number/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/number/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor
        
        Wenn kein nameDict angegeben ist dann wird der devicName + KeyName als frindlyName verwendet
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        dataNames: dict oder list. Bei einem dict werden nur die keys verwendet
        ignoreKeys: list. Diese keys werden ignoriert
        nameDict: dict. Hier koennen einzelne keys mit frindlyNames drin stehen
        minVal: dict Hier koennen einzelne keys mit dem minimal Slider Wert drin stehen. standard = 0
        maxVal: dict Hier koennen einzelne keys mit dem maximal Slider Wert drin stehen. standard = 100
        -t "homeassistant/number/slider1/config" -m '{"name": "Slider Test", "command_topic": "testSlider/state", "min":0, "max":100, "mode":"slider", "command_template": "{\"temperature\": {{ value }} }"}'
        """
        templateMsg = {"name": "", "command_topic":"", "min":0, "max":100, "mode":"slider", "command_template":""}

        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        templateMsg["command_template"] = cls._getCmdTemplate(sensorName)
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["min"] = minVal
        templateMsg["max"] = maxVal
            
        return templateMsg


    @classmethod
    def getDiscoverySwitchTopic(cls, deviceName, sensorName):
        return f"homeassistant/switch/{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoverySwitchCmd(cls,  deviceName, sensorName, niceName = ""):
        """
        https://www.home-assistant.io/docs/mqtt/discovery/
        topic "homeassistant/switch/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,

        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/switch/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein niceName angegeben ist dann wird der devicName + sensorName als frindlyName verwendet
        deviceName: wird zu bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        sensorName: Name des Sensors (normalerweise key im dict)
        """
        templateMsg = {"state_topic":"", "command_topic":"", "name": "", "value_template":"", "payload_on":"", "payload_off":"", "state_off":False, "state_on":True}

        templateMsg["state_topic"] = ThreadObject.createOutTopic(ThreadObject.createProjectTopic(deviceName))
        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["value_template"] = cls._getValueTemplateNonInt(sensorName)
        templateMsg["payload_on"] = cls._getPayloadOn(sensorName)
        templateMsg["payload_off"] = cls._getPayloadOff(sensorName)
        return templateMsg
