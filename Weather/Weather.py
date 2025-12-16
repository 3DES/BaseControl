import time
from Base.ThreadObject import ThreadObject
from Base.Supporter import Supporter

from Weather.dwd_forecast import DWD

class WetterDwd(ThreadObject):
    '''
    classdocs
    '''
    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.DAY_PREFIX = "Tag_"
        self.FORECAST_DAYS = 4
        self.REQUEST_TIME = 4*60*60   # We request all 4 hours
        self.tagsIncluded(["DwdStationId"])
        self.dwd = DWD()

    def getInitialWeatherDict(self):
        tempWeather = {}
        for day in range(self.FORECAST_DAYS):
            tempWeather[f"{self.DAY_PREFIX}{day}"] = {}
            tempWeather[f"{self.DAY_PREFIX}{day}"]["Sonnenstunden"] = 0
        return tempWeather

    def getSunArray(self, station_id, force_cache_refresh=False):
        self.dx = self.dwd.station_forecast(
            station_id, force_cache_refresh=force_cache_refresh
        )
        if self.dx is None:
            return None

        self.dxl = self.dx
        self.dxl["TTT"] = self.dxl["TTT"].apply(lambda x: x - 273.15)
        sunListHour = self.dxl["SunD1"].to_list()
        # convert sunList to percent per hour
        sunListHour[:] = [x / 3600 for x in sunListHour]

        return sunListHour

    def calculateSunPerDay(self, sunArray):
        sunPerDay = self.getInitialWeatherDict()
        for day in range(self.FORECAST_DAYS):
            tempSun = 0
            for hour in range(24):
                tempSun += sunArray[hour + (day*24)]
            sunPerDay[f"Tag_{day}"] = {}
            sunPerDay[f"Tag_{day}"][f"Sonnenstunden"] = int(tempSun)

        return sunPerDay

    def discoverNestedDict(self, nestedDict, equalSubKey):
        for key in nestedDict:
            if equalSubKey in str(nestedDict[key]):
                self.homeAutomation.mqttDiscoverySensor([f"{key}.{equalSubKey}"])

    def threadInitMethod(self):
        self.wetterdaten = {}
        self.initWeather = True

    def threadMethod(self):
        # check if a new msg is waiting
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.readMqttQueue(error = False)

        if self.timer(name = "Wetterabfrage", startTime = Supporter.getTimeOfToday(hour = 1), reSetup = True, timeout = self.REQUEST_TIME) or self.initWeather:
            try:
                self.wetterdaten.update(self.calculateSunPerDay(self.getSunArray(self.configuration["DwdStationId"])))
            except Exception as e:
                self.logger.error(self, f"Wetter Daten konnten nicht geholt werden! Internet, Netzwerk oder Funktion getSunArray() prüfen. {e}")
                self.wetterdaten.update(self.getInitialWeatherDict())

            # Initial wollen wir unsere Sensoren bei der Homeautomation anlegen
            if self.initWeather:
                self.discoverNestedDict(self.wetterdaten, "Sonnenstunden")
            self.initWeather = False

            outTopic = self.createOutTopic(self.getObjectTopic())
            self.mqttPublish(outTopic, self.wetterdaten, globalPublish = True, enableEcho = False)
            self.mqttPublish(outTopic, self.wetterdaten, globalPublish = False, enableEcho = False)


    def threadBreak(self):
        time.sleep(30)