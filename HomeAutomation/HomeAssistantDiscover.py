import json

from HomeAutomation.BaseHomeAutomation import BaseHomeAutomation
from Base.ThreadObject import ThreadObject
import re


class HomeAssistantDiscover(BaseHomeAutomation):
    '''
    classdocs
    '''
    @classmethod
    def _addPrefix(cls, niceName : str, prefix : str = ""):
        """
        When a homeAssistantPrefix has been defined in "Logger" configuration this prefix will be set and used whenever a sensor or actor is discovered
        """
        if len(BaseHomeAutomation.homeAutomationPrefix):
            return f"{BaseHomeAutomation.homeAutomationPrefix} {niceName}"
        else:
            return niceName

    @classmethod
    def _getFrindlyName(cls, deviceName, valueName) -> str:
        """
        devicename: normally objectname
        valuename: normally keyname from a dict. "PvPower" will be converted to "Pv Power"
        deletes all "."
        return devicename + converted valueName
        """
        newName = " ".join(re.findall('[a-z]+|[A-Z][^A-Z]*', valueName))
        sensorName = deviceName + " " + newName
        return sensorName.replace(".", "")

    @classmethod
    def _getValueTemplateInt(cls, name : str, subStructure : str = None) -> str:
        valueTemplate = ((subStructure + ".") if subStructure is not None else "") + name
        return r"{{ value_json.%s | float|round(2) }}" %valueTemplate

    @classmethod
    def _getValueTemplateNonInt(cls, name : str, subStructure : str = None) -> str:
        valueTemplate = ((subStructure + ".") if subStructure is not None else "") + name
        return r"{{ value_json.%s }}" %valueTemplate

    @classmethod
    def _getCmdTemplate(cls, name) -> str:
        return r'{"%s": {{ value }} }' %name

    @classmethod
    def _getCmdStrTemplate(cls, name) -> str:
        return r'{"%s": "{{ value }}" }' %name

    @classmethod
    def _getPayloadOn(cls, name) -> str:
        return r'{"%s" : true}' %name

    @classmethod
    def _getPayloadOff(cls, name) -> str:
        return r'{"%s" : false}' %name

    @classmethod
    def prepareNameForTopicUse(cls, name) -> str:
        forbiddenChar = [".","/"," "]
        for char in forbiddenChar:
            name = name.replace(char, "_")
        return name

    @classmethod
    def _getUnitOfMeasurement(cls, valueName) -> str:
        units = {"W":["power"], "A":["curr", "battdischarge", "battcharge"], "kWh":["daily", "produ"], "V":["spannung", "voltage", "vmin", "vmax"], "%":["prozent"], "°C":["temperature"]}
        for unit in units:
            for segment in units[unit]:
                if segment in valueName.lower():
                    return unit
        return ""


    @classmethod
    def getDiscoveryTextTopic(cls, deviceName : str, sensorName : str) -> str:
        textTopic = f'homeassistant/text/{ThreadObject.get_projectName()}_{deviceName}'
        if sensorName is not None:
            textTopic += f"_{cls.prepareNameForTopicUse(sensorName)}"
        textTopic += '/config'
        return textTopic


    @classmethod
    def getDiscoverySensorTopic(cls, deviceName : str, sensorName : str, readOnly : bool = False) -> str:
        return f'homeassistant/{"sensor" if not readOnly else "binary_sensor"}/{ThreadObject.get_projectName()}_{deviceName}_{cls.prepareNameForTopicUse(sensorName)}/config'


    @classmethod
    def getDiscoverySensorCmd(cls, deviceName : str, sensorName : str, niceName : str, unit : str, topic : str, subStructure : str = None, payloadOff = None, payloadOn = None) -> dict:
        """
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        topic "homeassistant/sensor/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/binary_sensor/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein niceName angegeben ist dann wird er gebildet. s. _getFrindlyName
        Wenn kein unitDict angegeben ist dann wird versucht die Einheit aus dem Keyname abzuleiten
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        sensorName: Name des Sensors
        niceName: Hier kann der FrindlyName drin stehen
        unit: hier kann die jeweilige Einheit drin stehen.
        """
        templateMsg = {"state_topic" : topic, "name" : "", "value_template" : "", "unit_of_measurement" : ""}

        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["name"] = cls._addPrefix(templateMsg["name"])

        if unit == "none":
            del templateMsg["unit_of_measurement"]
        elif len(unit):
            templateMsg["unit_of_measurement"] = unit
        else:
            templateMsg["unit_of_measurement"] = cls._getUnitOfMeasurement(sensorName)
            if not len(templateMsg["unit_of_measurement"]):
                del templateMsg["unit_of_measurement"]

        # we assume that every value with unit is a int or float, and we have to use _getValueTemplateInt()
        if ("unit_of_measurement" in templateMsg) and len(templateMsg["unit_of_measurement"]):
            templateMsg["value_template"] = cls._getValueTemplateInt(sensorName, subStructure)
        else:
            templateMsg["value_template"] = cls._getValueTemplateNonInt(sensorName, subStructure)

        if payloadOn is not None:
            templateMsg["payload_on"] = payloadOn

        if payloadOff is not None:
            templateMsg["payload_off"] = payloadOff

        return templateMsg


    @classmethod
    def getDiscoverySelectorTopic(cls, deviceName : str, sensorName : str) -> str:
        return f"homeassistant/select/{ThreadObject.get_projectName()}_{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoverySelectorCmd(cls,  deviceName : str, optionList : str, niceName : str = "") -> dict:
        """
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        topic "homeassistant/switch/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/switch/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein niceName angegeben ist dann wird er gebildet. s. _getFrindlyName
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        optionList: Liste der eintrage der auswahlbox
        niceName: Hier kann der FrindlyName drin stehen
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
        templateMsg["name"] = cls._addPrefix(templateMsg["name"])
        templateMsg["options"] = optionList
        return templateMsg


    @classmethod
    def getDiscoveryInputNumberSliderTopic(cls, deviceName : str, sensorName : str) -> str:
        return f"homeassistant/number/{ThreadObject.get_projectName()}_{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoveryInputNumberSliderCmd(cls,  deviceName : str, sensorName : str, niceName : str = "", minVal = 0, maxVal = 100, stateTopic : str = None, valueTemplate : str = None) -> dict:
        """
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        topic "homeassistant/number/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,
        
        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/number/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor
        
        Wenn kein niceName angegeben ist dann wird er gebildet. s. _getFrindlyName
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        sensorName: Name des Sensors
        niceName: Hier kann der FrindlyName drin stehen
        minVal: dict Hier koennen einzelne keys mit dem minimal Slider Wert drin stehen. standard = 0
        maxVal: dict Hier koennen einzelne keys mit dem maximal Slider Wert drin stehen. standard = 100
        -t "homeassistant/number/slider1/config" -m '{"name": "Slider Test", "command_topic": "testSlider/state", "min":0, "max":100, "mode":"slider", "command_template": "{\"temperature\": {{ value }} }"}'
        """
        templateMsg = {"mode":"slider"}

        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        templateMsg["command_template"] = cls._getCmdTemplate(sensorName)
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["name"] = cls._addPrefix(templateMsg["name"])
        templateMsg["min"] = minVal
        templateMsg["max"] = maxVal
        if stateTopic is not None:
            templateMsg["state_topic"] = stateTopic
        if valueTemplate is not None:
            templateMsg["value_template"] = valueTemplate

        return templateMsg


    @classmethod
    def getDiscoverySwitchTopic(cls, deviceName : str, sensorName : str) -> str:
        return f"homeassistant/switch/{ThreadObject.get_projectName()}_{deviceName}_{sensorName}/config"

    @classmethod
    def getDiscoverySwitchCmd(cls,  deviceName : str, sensorName : str, niceName : str = "", subStructure : str = None, payloadOff = None, payloadOn = None, stateOff = None, stateOn = None, icon = None) -> dict:
        """
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        topic "homeassistant/switch/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,

        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/switch/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein niceName angegeben ist dann wird er gebildet. s. _getFrindlyName
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        sensorName: Name des Sensors
        niceName: Hier kann der FrindlyName drin stehen
        """
        templateMsg = {"state_topic":"", "command_topic":"", "name": "", "value_template":"", "payload_on":"", "payload_off":"", "state_off":False, "state_on":True}

        templateMsg["state_topic"] = ThreadObject.createOutTopic(ThreadObject.createProjectTopic(deviceName))
        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["name"] = cls._addPrefix(templateMsg["name"])
        templateMsg["value_template"] = cls._getValueTemplateNonInt(sensorName, subStructure)

        if payloadOn is not None:
            templateMsg["payload_on"] = payloadOn
            if stateOn is not None:
                templateMsg["state_on"] = stateOn
            else:
                templateMsg["state_on"] = payloadOn
        else:
            templateMsg["payload_on"] = cls._getPayloadOn(sensorName)

        if payloadOff is not None:
            templateMsg["payload_off"] = payloadOff
            if stateOn is not None:
                templateMsg["state_off"] = stateOff
            else:
                templateMsg["state_off"] = payloadOff
        else:
            templateMsg["payload_off"] = cls._getPayloadOff(sensorName)

        if icon is not None:
            templateMsg["icon"] = icon

        return templateMsg


    @classmethod
    def getDiscoverySwitchOptimisticStringCmd(cls,  deviceName : str, sensorName : str, onCmd : str, offCmd : str, niceName : str = "") -> dict:
        """
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        topic "homeassistant/switch/garden/config"
        garden muss uniqe sein, die MSG muss retained sein,

        message '{"name": "garden", "device_class": "motion", "state_topic": "homeassistant/switch/garden/state"}'
        alle REQUIRED Values muessen enthalten sein, siehe dokumentation von z.b. binary_sensor oder sensor

        Wenn kein niceName angegeben ist dann wird er gebildet. s. _getFrindlyName
        deviceName: wird zum bilden des SensorTopics verwendet "BMS" wird zu "ProjektName/BMS/out"
        sensorName: Name des Sensors
        niceName: Hier kann der FrindlyName drin stehen
        """
        templateMsg = {"command_topic":"", "name": "", "payload_on":"", "payload_off":""}

        templateMsg["command_topic"] = ThreadObject.createInTopic(ThreadObject.createProjectTopic(deviceName))
        if len(niceName):
            templateMsg["name"] = niceName
        else:
            templateMsg["name"] = cls._getFrindlyName(deviceName, sensorName)
        templateMsg["name"] = cls._addPrefix(templateMsg["name"])
        templateMsg["payload_on"] = onCmd
        templateMsg["payload_off"] = offCmd
        return templateMsg

