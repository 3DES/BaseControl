import time
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter

try:
    from Weather.DWD import DWD
except ImportError:
    from DWD import DWD



class WetterDwd(ThreadObject):
    DAY_PREFIX = "Tag_"
    FORECAST_DAYS = 7
    REQUEST_TIME = 4*60*60   # We request all 4 hours
    SLEEP_TIME = 30



    '''
    classdocs
    '''
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["DwdStationId"])
        self.dwd = DWD(self.configuration["DwdStationId"])
        self.removeMqttRxQueue()        # mqttRxQueue has to be removed if it's not needed!


    def getWeatherDict(self, sunHours : list = None):
        tempWeather = {}
        for index, day in enumerate(range(self.FORECAST_DAYS)):
            tempWeather[f"{self.DAY_PREFIX}{day}"] = {}
            tempWeather[f"{self.DAY_PREFIX}{day}"]["Sonnenstunden"] = 0 if sunHours is None else sunHours[index]
        return tempWeather


    def discoverNestedDict(self, nestedDict, equalSubKey):
        for key in nestedDict:
            if equalSubKey in str(nestedDict[key]):
                self.homeAutomation.mqttDiscoverySensor([f"{key}.{equalSubKey}"], unitDict = {f"{key}.{equalSubKey}" : "h"})


    def threadInitMethod(self):
        self.wetterdaten = {}
        self.initWeather = True


    def threadMethod(self):
        if self.timer(name = "Wetterabfrage", startTime = Supporter.getTimeOfToday(hour = 1), firstTimeTrue = True, autoReset = True, timeout = self.REQUEST_TIME):
            try:
                self.dwd.update()           # update weather data
                key = "SunD1"               # we want SunD1 values
                unit = self.dwd.descriptions[key]["UnitOfMeasurement"]      # get weather data unit (should be seconds)
                short_list = self.dwd.get_daily_list(key = key, daily_correction = 0, converted = True, noOldData = True)
                sunHours = [round(short_list[key], 1) for key in sorted(short_list.keys())[:self.FORECAST_DAYS]]

                #Supporter.write_data_to_file("output.txt", short_list)
                #Supporter.write_data_to_file("output.txt", sunHours, "sun hours")
                #Supporter.write_data_to_file("output.txt", self.dwd.get_raw_values([key, "Rad1h", "TTT", "SunD"]), "data")
                #Supporter.write_data_to_file("raw_weather_data.txt", self.dwd.get_raw_values(key))
                #Supporter.write_data_to_file("raw_weather_data.csv", self.dwd.get_combined_values([key, "Rad1h", "TTT", "SunD"]))
                
                self.wetterdaten.update(self.getWeatherDict(sunHours))
            except Exception as e:
                self.logger.error(self, f"Wetter Daten konnten nicht geholt werden! {e}")
                self.wetterdaten.update(self.getWeatherDict())

            # Initial wollen wir unsere Sensoren bei der Homeautomation anlegen
            if self.initWeather:
                self.discoverNestedDict(self.wetterdaten, "Sonnenstunden")
            self.initWeather = False

            outTopic = self.createOutTopic(self.getObjectTopic())
            self.mqttPublish(outTopic, self.wetterdaten, globalPublish = True, enableEcho = False)
            self.mqttPublish(outTopic, self.wetterdaten, globalPublish = False, enableEcho = False)


    def threadBreak(self):
        time.sleep(self.SLEEP_TIME)



if __name__ == "__main__":
    from Logger.Logger import Logger
    loggerConfiguration = {
        "projectName": "AccuTester",
        "homeAutomation": "HomeAutomation.HomeAssistantDiscover.HomeAssistantDiscover",
        "homeAutomationPrefix": "X1"    
    }
    WetterDwd.logger = Logger(threadName = "Logger", configuration = loggerConfiguration, interfaceQueues = None)

    configuration = { "DwdStationId": "10384" }
    wetter = WetterDwd(threadName = "Wetter", configuration = configuration)
    WetterDwd.REQUEST_TIME = 5
    WetterDwd.SLEEP_TIME = 1
    wetter.threadInitMethod()

    while True:
        wetter.threadMethod()
        wetter.threadBreak()
