import requests
import zipfile
import io
import xmltodict
import time
from datetime import datetime, timedelta
from typing import Union



class DWD:
    _TODAY_IS_YESTERDAY = -1
    _TODAY_IS_TODAY     = 0
    _TODAY_IS_TOMORROW  = +1
    def __init__(self, station_number):
        self.station_number = station_number
        self.url = f"https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_L/single_stations/{station_number}/kml/MOSMIX_L_LATEST_{station_number}.kmz"
        self.station_url = f"https://www.dwd.de/DE/leistungen/met_verfahren_mosmix/mosmix_stationskatalog.cfg?view=nasPublication"
        self.description_url = f"https://opendata.dwd.de/weather/lib/MetElementDefinition.xml"
        self.get_value_descriptions()
        self.get_weather_data()

    def download_file(self, url : str = None):
        """Download the KMZ file from the URL."""
        max_retries = 5
        attempt = 0
        while attempt < max_retries:
            try:
                response = requests.get(url if url is not None else self.url)
                response.raise_for_status()  # Raises an error for bad HTTP status codes
                return response.content
            except requests.exceptions.RequestException as e:
                attempt += 1
                time.sleep(.5)
        
        print(f"Error downloading the file: {e}")
        return None

    def extract_kml_from_zip(self, file_content):
        """Extract KML/XML from the KMZ (ZIP) file."""
        try:
            with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
                # Check if the ZIP archive contains any files
                if not zf.namelist():
                    print("Error: ZIP archive is empty.")
                    return None

                # Search for the XML or KML file inside the ZIP archive
                for file_name in zf.namelist():
                    if file_name.endswith((".xml", ".kml")):  # Looking for .xml or .kml files
                        with zf.open(file_name) as kml_file:
                            return kml_file.read()

                print("Error: No KML/XML file found in the ZIP archive.")
                return None
        except zipfile.BadZipFile:
            print("Error: Invalid ZIP file or corrupted archive.")
        except Exception as e:
            print(f"Unexpected error during unzip process: {e}")
        return None

    def get_weather_data(self):
        '''
        Fetch, extract, and parse the KML/XML file
        '''
        file_content = self.download_file()
        if file_content:
            kml_content = self.extract_kml_from_zip(file_content)
            if kml_content:
                data = xmltodict.parse(kml_content)
                self.station_name = data["kml:kml"]["kml:Document"]["kml:Placemark"]["kml:description"]
                self.station_coordinates = data["kml:kml"]["kml:Document"]["kml:Placemark"]["kml:Point"]["kml:coordinates"]
                self.time_stamps = data["kml:kml"]["kml:Document"]["kml:ExtendedData"]["dwd:ProductDefinition"]["dwd:ForecastTimeSteps"]["dwd:TimeStep"]

                self.values = {}
                for entry in data["kml:kml"]["kml:Document"]["kml:Placemark"]["kml:ExtendedData"]["dwd:Forecast"]:
                    self.values[entry["@dwd:elementName"]] = entry["dwd:value"].split()
        # search for missing keys
        self.keys_only_in_description = set(self.descriptions.keys()) - set(self.values.keys())
        self.keys_only_in_values = set(self.values.keys()) - set(self.descriptions.keys())

    def get_station_names(self):
        station_lines = self.download_file(self.station_url).decode("ISO-8859-1").split("\n")
        stations = {}
        for line in station_lines[2:]:
            parts = line.split()
            if parts:
                key = parts[0]
                value = parts[1:]
                stations[key] = value

        if self.station_number in stations:
            self.station_name = stations[self.station_number]
            print(f"{self.station_number}: f{stations[self.station_number]}")
        else:
            print(f"ERROR: station {self.station_number} not found")

    def get_value_descriptions(self):
        xml_content = self.download_file(self.description_url)
        if xml_content:
            data = xmltodict.parse(xml_content)
            self.descriptions = {}
            for entry in data["MetElementDefinition"]["MetElement"]:
                self.descriptions[entry["ShortName"]] = {}
                for key in entry.keys():
                    if key != "ShortName":
                        self.descriptions[entry["ShortName"]][key] = entry[key]

    def get_date(self, time_stamp : str):
        return datetime.strptime(time_stamp, "%Y-%m-%dT%H:%M:%S.%fZ").date()

    def correct_date(self, time_stamp : Union[datetime, str], daily_correction : int = 0):
        back_to_string = False
        if isinstance(time_stamp, str):
            back_to_string = True
            time_stamp = datetime.strptime(time_stamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        time_stamp += timedelta(days=daily_correction)
        if back_to_string:
            time_stamp = time_stamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return time_stamp

    def the_day_before(self, time_stamp : str):
        '''
        Convert given time stamp to the day before. That's useful for values that are "yesterday" values
        '''
        return self.correct_date(time_stamp, -1)

    def the_day_after(self, time_stamp : str):
        '''
        Convert given time stamp to the day after. That's useful for values that are "tomorrow" values
        '''
        return self.correct_date(time_stamp, +1)

    def get_available_keys(self):
        '''
        Return all available keys (in self.descriptions.keys() there could be more but in that case there are no values for such keys)
        '''
        return sorted(self.values.keys())

    def print_station_information(self):
        print(f"Station ID ............ {self.station_number}")
        print(f"Station Name .......... {self.station_name}")
        print(f"Station coordinates ... {self.station_coordinates}")
        
    def print_key_header(self, key : str):
        print(f"Value ................. {key}")
        print(f"Description ........... {self.descriptions[key]['Description']}")

    def print_key_unit(self, key : str):
        print(f"Unit .................. {self.descriptions[key]['UnitOfMeasurement']}")

    def get_unit(self, key : str):
        '''
        Retun the unit of the given key
        '''
        return self.descriptions[key]["UnitOfMeasurement"]

    def convert_unit(self, key : str, value : float):
        '''
        For some values a conversion is supported, if that's the case give the converted value
        '''
        unit = self.get_unit(key)
        if unit == "s":
            return value / 3600
        elif unit == "kJ/m2":
            return round(value / 3.6, 2)
        elif unit == "K":
            return round(value - 273.15)
        else:
            return None

    def get_converted_unit(self, key : str):
        '''
        For some values a conversion is supported, if that's the case give the unit of the converted value
        '''
        unit = self.get_unit(key)
        if unit == "s":
            return "h"
        elif unit == "kJ/m2":
            return "Wh/m2"
        elif unit == "K":
            return "C"
        else:
            return None

    def get_compressed_list(self, key : str, daily_correction : int = 0, converted : bool = False):
        '''
        Takes all non-empty entries, "-" entries will be ignored
        '''
        compressed_list = {}
        for index, time_stamp in enumerate(self.time_stamps):
            if self.values[key][index] != "-":
                if converted:
                    compressed_list[self.correct_date(time_stamp, daily_correction)] = self.convert_unit(key, float(self.values[key][index]))
                else:
                    compressed_list[self.correct_date(time_stamp, daily_correction)] = float(self.values[key][index])
        return compressed_list

    def get_daily_list(self, key : str, daily_correction : int = 0, converted : bool = False):
        '''
        Takes all entries of a given key and creates a list with only one entry per day, all partial entries are summed up
        @param daily_correction:    time stamps in list will be corrected if given, value is in whole days, -1 will correct each time stamp to the day before, +1 will correct each time stamp to the day after
        '''
        # sum up value
        if self.get_unit(key) not in ["s", "kJ/m2"]:        # others usually don't make sense to create a daily list out of, i.e. K means sum all up and subtract 273.15 makes absolutely no sense!
            return {}
        currentDay = self.get_date(self.time_stamps[0])     # get the first time stamp from the values list, it's always the same since there is only one time stamp list
        sum = 0
        daily_list = {}
        summed_up_this_day = False      # important, because get_compressed_list() will throw away whole days if there are only "-" values so get_daily_list() should have the same behavior
        for index, time_stamp in enumerate(self.time_stamps):
            elementDay = self.get_date(time_stamp)
            if elementDay == currentDay:
                if self.values[key][index] != "-":
                    sum += float(self.values[key][index])
                    summed_up_this_day = True
            if (elementDay != currentDay) or (index == len(self.time_stamps) - 1):
                if summed_up_this_day:
                    if converted:
                        sum = self.convert_unit(key, sum)
                    daily_list[self.correct_date(currentDay, daily_correction)] = sum
                    summed_up_this_day = False
                if self.values[key][index] != "-":
                    sum = float(self.values[key][index])     # take over current value otherwise it will be missed
                    summed_up_this_day = True
                else:
                    sum = 0
                if summed_up_this_day:
                    if (elementDay != currentDay) and (index == len(self.time_stamps) - 1):
                        if converted:
                            sum = self.convert_unit(key, sum)
                        daily_list[self.correct_date(elementDay, daily_correction)] = sum      # last element is from next day, so it has to be handled separatey because in that case code will not return to this position!
                    summed_up_this_day = False
                currentDay = elementDay
        return daily_list



def main():
    # Example station number
    station_number = "10384"
    #values = ["TTT", "TN", "FF"]
    #values = ["SunD", "SunD1", "Rad1h"]
    #values = ["TTT", "SunD1"]
    values = ["SunD1", "SunD"]
    short = True
    long  = False
    convert = True
    daily_correction = DWD._TODAY_IS_YESTERDAY        # values are given as "yesterday values", correct day by one to get current day





    # Create instance of DWD
    dwd = DWD(station_number)
    ###dwd.get_station_names()
    ###dwd.get_value_descriptions()
    ###dwd.get_weather_data()

    # show all keys
    print(dwd.get_available_keys())

    # print complete list for one key
    if dwd.keys_only_in_description:
        print(f"keys only in description: {sorted(dwd.keys_only_in_description)}")
    if dwd.keys_only_in_values:
        print(f"keys only in values: {sorted(dwd.keys_only_in_values)}")

    dwd.print_station_information()

    for key in values:
        if key == "SunD":
            daily_correction = DWD._TODAY_IS_YESTERDAY        # values are given as "yesterday values", correct day by one to get current day
        else:
            daily_correction = DWD._TODAY_IS_TODAY
        if key not in dwd.values:
            print(f"key {key} is unknown!")
        else:
            dwd.print_key_header(key)
            dwd.print_key_unit(key)
            unit = dwd.descriptions[key]["UnitOfMeasurement"]

            if long:
                # show all available entries for that key
                compressed_list = dwd.get_compressed_list(key, daily_correction, converted = convert)
                for time_stamp in sorted(compressed_list.keys()):
                    unit = dwd.get_converted_unit(key) if convert else dwd.get_unit(key)
                    print(f"{time_stamp}: {compressed_list[time_stamp]:.1f} {unit}")

            print("------------------")

            if short:
                short_list = dwd.get_daily_list(key, daily_correction, converted = convert)
                for time_stamp in sorted(short_list.keys())[:4]:
                    unit = dwd.get_converted_unit(key) if convert else dwd.get_unit(key)
                    print(f"{time_stamp}: {short_list[time_stamp]:.1f} {unit}")

            print("======================================================")

            

if __name__ == "__main__":
    main()



