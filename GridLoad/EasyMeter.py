import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
from Base.MqttBase import MqttBase
import Base
import subprocess
import Base.Crc
from queue import Queue
import colorama
import functools


import sys
import re


# dummy values for SIMULATE
#21456 2023-10-22 15:22:00.801537  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 6, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037634.4302', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4197.47', '36.7.0': '-294.66', '56.7.0': '-1997.50', '76.7.0': '-1905.30', '32.7.0': '225.4', '52.7.0': '231.6', '72.7.0': '228.8', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#40641 2023-10-22 15:23:00.152269  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 12, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037714.5230', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4424.02', '36.7.0': '-306.07', '56.7.0': '-2128.17', '76.7.0': '-1989.77', '32.7.0': '226.2', '52.7.0': '231.3', '72.7.0': '229.8', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#59612 2023-10-22 15:24:00.507630  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 17, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037753.7990', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-635.30', '36.7.0': '-10.69', '56.7.0': '-390.51', '76.7.0': '-234.08', '32.7.0': '224.9', '52.7.0': '226.5', '72.7.0': '226.0', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#79167 2023-10-22 15:25:00.928210  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 23, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037825.4329', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4329.76', '36.7.0': '-207.94', '56.7.0': '-2087.72', '76.7.0': '-2034.10', '32.7.0': '226.2', '52.7.0': '232.2', '72.7.0': '230.2', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#98244 2023-10-22 15:26:00.248419  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 28, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037878.1654', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4191.28', '36.7.0': '-193.60', '56.7.0': '-2036.60', '76.7.0': '-1961.07', '32.7.0': '226.7', '52.7.0': '232.2', '72.7.0': '229.8', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#117746 2023-10-22 15:27:00.666255  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 33, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10037930.2376', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-2390.21', '36.7.0': '-94.83', '56.7.0': '-1195.16', '76.7.0': '-1100.20', '32.7.0': '226.8', '52.7.0': '231.0', '72.7.0': '229.4', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#137026 2023-10-22 15:28:01.016414  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 39, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10038002.5580', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4317.74', '36.7.0': '-262.16', '56.7.0': '-2085.64', '76.7.0': '-1969.94', '32.7.0': '226.9', '52.7.0': '232.0', '72.7.0': '229.9', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#155765 2023-10-22 15:29:00.566803  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 44, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697980857.082003, 'previousPower': 0, 'previousReduction': 0, 'previousTimestamp': 0, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10038067.5449', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4230.82', '36.7.0': '-245.07', '56.7.0': '-2049.07', '76.7.0': '-1936.67', '32.7.0': '227.1', '52.7.0': '231.8', '72.7.0': '230.1', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#174859 2023-10-22 15:30:00.022869  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 50, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697981400.0209885, 'previousPower': 0, 'previousReduction': 1000, 'previousTimestamp': 1697980857.082003, 'updatePowerValue': True, '1.8.0': '3847490.3616', '2.8.0': '10038144.4504', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4157.63', '36.7.0': '-237.25', '56.7.0': '-2014.62', '76.7.0': '-1905.75', '32.7.0': '227.3', '52.7.0': '232.2', '72.7.0': '230.1', '199.130.3': 'E S Y'} (EasyMeter.py:457)
#194105 2023-10-22 15:31:00.418638  [LOG_LEVEL.INFO]   "THREAD EasyMeterGridSide [GridLoad.EasyMeter]" : new message: {'validMessages': 55, 'invalidMessages': 0, 'lastInvalidMessageTimeStamp': 0, 'invalidMessageError': 0, 'allowedPower': 0, 'allowedReduction': 1000, 'allowedTimestamp': 1697981400.0209885, 'previousPower': 0, 'previousReduction': 1000, 'previousTimestamp': 1697980857.082003, 'updatePowerValue': False, '1.8.0': '3847490.3616', '2.8.0': '10038207.7540', '1.8.1': '398.4228', '1.8.2': '3847091.9387', '16.7.0': '-4036.06', '36.7.0': '-162.33', '56.7.0': '-2001.53', '76.7.0': '-1872.19', '32.7.0': '227.2', '52.7.0': '231.8', '72.7.0': '229.7', '199.130.3': 'E S Y'} (EasyMeter.py:457)


class EasyMeter(ThreadObject):
    '''
    classdocs
    
    http://www.stefan-weigert.de/php_loader/sml.php
    https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Publikationen/TechnischeRichtlinien/TR03109/TR-03109-1_Anlage_Feinspezifikation_Drahtgebundene_LMN-Schnittstelle_Teilb.pdf?__blob=publicationFile
    '''

    # patterns to match messages and values
    DELIVERED_ENERGY_KEY = "2.8.0"
    RECEIVED_ENERGY_KEY  = "1.8.0"
    CURRENT_POWER_KEY    = "16.7.0"
    CURRENT_POWER_L1_KEY = "36.7.0"
    CURRENT_POWER_L2_KEY = "56.7.0"
    CURRENT_POWER_L3_KEY = "76.7.0"
    L1_VOLTAGE_KEY       = "32.7.0"
    L2_VOLTAGE_KEY       = "52.7.0"
    L3_VOLTAGE_KEY       = "72.7.0"

    # "0.0.0"              -> '\x77\x07\x01\x00\x00\x00\x00\xFF\x01\x01\x01\x01\x0F(.{14})\x01',           -> 'w\x07\x01\x00\x00\x00\x00\xFF\x01\x01\x01\x01\x0F(.{14})\x01',          
    # "0.0.9"              -> '\x77\x07\x01\x00\x00\x00\x09\xFF\x01\x01\x01\x01\x0B(.{10})\x01',           -> 'w\x07\x01\x00\x00\x00\x09\xFF\x01\x01\x01\x01\x0B(.{10})\x01',          
    # RECEIVED_ENERGY_KEY  -> '\x77\x07\x01\x00\x01\x08\x00\xFF\x64...\x01\x62\x1E\x52\xFC\x59(.{8})\x01', -> 'w\x07\x01\x00\x01\x08\x00\xFFd...\x01b\x1ER\xFCY(.{8})\x01',
    # DELIVERED_ENERGY_KEY -> '\x77\x07\x01\x00\x02\x08\x00\xFF\x64...\x01\x62\x1E\x52\xFC\x59(.{8})\x01', -> 'w\x07\x01\x00\x02\x08\x00\xFFd...\x01b\x1ER\xFCY(.{8})\x01',
    # "1.8.1"              -> '\x77\x07\x01\x00\x01\x08\x01\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',    -> 'w\x07\x01\x00\x01\x08\x01\xFF\x01\x01b\x1ER\xFCY(.{8})\x01',   
    # "1.8.2"              -> '\x77\x07\x01\x00\x01\x08\x02\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',    -> 'w\x07\x01\x00\x01\x08\x02\xFF\x01\x01b\x1ER\xFCY(.{8})\x01',   
    # CURRENT_POWER_KEY    -> '\x77\x07\x01\x00\x10\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    -> 'w\x07\x01\x00\x10\x07\x00\xFF\x01\x01b\x1BR\xFEY(.{8})\x01',   
    # CURRENT_POWER_L1_KEY -> '\x77\x07\x01\x00\\\x24\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',  -> 'w\x07\x01\x00\\$\x07\x00\xFF\x01\x01b\x1BR\xFEY(.{8})\x01', 
    # CURRENT_POWER_L2_KEY -> '\x77\x07\x01\x00\x38\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    -> 'w\x07\x01\x008\x07\x00\xFF\x01\x01b\x1BR\xFEY(.{8})\x01',   
    # CURRENT_POWER_L3_KEY -> '\x77\x07\x01\x00\x4C\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    -> 'w\x07\x01\x00L\x07\x00\xFF\x01\x01b\x1BR\xFEY(.{8})\x01',   
    # L1_VOLTAGE_KEY       -> '\x77\x07\x01\x00\x20\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    -> 'w\x07\x01\x00 \x07\x00\xFF\x01\x01b#R\xFFc(.{2})\x01',   
    # L2_VOLTAGE_KEY       -> '\x77\x07\x01\x00\x34\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    -> 'w\x07\x01\x004\x07\x00\xFF\x01\x01b#R\xFFc(.{2})\x01',   
    # L3_VOLTAGE_KEY       -> '\x77\x07\x01\x00\x48\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    -> 'w\x07\x01\x00H\x07\x00\xFF\x01\x01b#R\xFFc(.{2})\x01',   
    # "199.130.3"          -> '\x77\x07\x81\x81\xC7\x82\x03\xFF\x01\x01\x01\x01\x04(.{3})\x01',            -> 'w\x07\x81\x81\xC7\x82\x03\xFF\x01\x01\x01\x01\x04(.{3})\x01',           
    # "199.130.5"          -> '\x77\x07\x81\x81\xC7\x82\x05\xFF\x01\x01\x01\x01\x83\x02(.{48})\x01',       -> 'w\x07\x81\x81\xC7\x82\x05\xFF\x01\x01\x01\x01\x83\x02(.{48})\x01',      
    # "199.240.6"          -> '\x77\x07\x81\x81\xC7\xF0\x06\xFF\x01\x01\x01\x01\x04(.{3})\x01',            -> 'w\x07\x81\x81\xC7\xF0\x06\xFF\x01\x01\x01\x01\x04(.{3})\x01',              
    
    SML_VALUES = {
        # key = OBIS no., "fullname" = OBIS number with leading values                                                   
        # "resolution" = 1 -> 0.1, 2 -> 0.01, ... n -> 10^(-n), hex = hexstring, dump = printable characters + others as hex value
        # "unit" = unit AFTER value has been recalculated with given "resolution"
        "0.0.0"              : { "fullname" : "1-0:0.0.0",                   "regex" : re.compile(b'\x77\x07\x01\x00\x00\x00\x00\xFF\x01\x01\x01\x01\x0F(.{14})\x01',           re.MULTILINE | re.DOTALL), "resolution" : "dump", "unit" : "",    "ignore" : True,                    "description" : "serial" },                          # "Seriennummer"
        "0.0.9"              : { "fullname" : "1-0:0.0.9",                   "regex" : re.compile(b'\x77\x07\x01\x00\x00\x00\x09\xFF\x01\x01\x01\x01\x0B(.{10})\x01',           re.MULTILINE | re.DOTALL), "resolution" : "hex",  "unit" : "",    "ignore" : True,                    "description" : "serverID" },                        # "Server-ID"
        RECEIVED_ENERGY_KEY  : { "fullname" : "1-0:" + RECEIVED_ENERGY_KEY,  "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x00\xFF\x64...\x01\x62\x1E\x52\xFC\x59(.{8})\x01', re.MULTILINE | re.DOTALL), "resolution" : 7,      "unit" : "kWh", "ignore" : False, "signed" : False, "description" : "positiveActiveEnergyTotal" },       # "Bezug total"
        DELIVERED_ENERGY_KEY : { "fullname" : "1-0:" + DELIVERED_ENERGY_KEY, "regex" : re.compile(b'\x77\x07\x01\x00\x02\x08\x00\xFF\x64...\x01\x62\x1E\x52\xFC\x59(.{8})\x01', re.MULTILINE | re.DOTALL), "resolution" : 7,      "unit" : "kWh", "ignore" : False, "signed" : False, "description" : "negativeActiveEnergyTotal" },       # "Lieferung total"
        "1.8.1"              : { "fullname" : "1-0:1.8.1",                   "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x01\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 7,      "unit" : "kWh", "ignore" : False, "signed" : False, "description" : "positiveActiveEnergyT1"    },       # "Bezug Tarif1"
        "1.8.2"              : { "fullname" : "1-0:1.8.2",                   "regex" : re.compile(b'\x77\x07\x01\x00\x01\x08\x02\xFF\x01\x01\x62\x1E\x52\xFC\x59(.{8})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 7,      "unit" : "kWh", "ignore" : False, "signed" : False, "description" : "positiveActiveEnergyT2"    },       # "Bezug Tarif2"
        CURRENT_POWER_KEY    : { "fullname" : "1-0:" + CURRENT_POWER_KEY,    "regex" : re.compile(b'\x77\x07\x01\x00\x10\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 2,      "unit" : "W",   "ignore" : False, "signed" : True,  "description" : "activeInstantaneousPower"  },       # "Momentanleistung gesammt, vorzeichenbehaftet"
        CURRENT_POWER_L1_KEY : { "fullname" : "1-0:" + CURRENT_POWER_L1_KEY, "regex" : re.compile(b'\x77\x07\x01\x00\\\x24\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',  re.MULTILINE | re.DOTALL), "resolution" : 2,      "unit" : "W",   "ignore" : False, "signed" : True,  "description" : "activeInstantaneousPowerL1"},       # "Momentanleistung L1, vorzeichenbehaftet"
        CURRENT_POWER_L2_KEY : { "fullname" : "1-0:" + CURRENT_POWER_L2_KEY, "regex" : re.compile(b'\x77\x07\x01\x00\x38\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 2,      "unit" : "W",   "ignore" : False, "signed" : True,  "description" : "activeInstantaneousPowerL2"},       # "Momentanleistung L2, vorzeichenbehaftet"
        CURRENT_POWER_L3_KEY : { "fullname" : "1-0:" + CURRENT_POWER_L3_KEY, "regex" : re.compile(b'\x77\x07\x01\x00\x4C\x07\x00\xFF\x01\x01\x62\x1B\x52\xFE\x59(.{8})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 2,      "unit" : "W",   "ignore" : False, "signed" : True,  "description" : "activeInstantaneousPowerL3"},       # "Momentanleistung L3, vorzeichenbehaftet"
        L1_VOLTAGE_KEY       : { "fullname" : "1-0:" + L1_VOLTAGE_KEY,       "regex" : re.compile(b'\x77\x07\x01\x00\x20\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 1,      "unit" : "V",   "ignore" : False, "signed" : False, "description" : "instantaneousVoltageL1"    },       # "aktuelle Spannung L1"
        L2_VOLTAGE_KEY       : { "fullname" : "1-0:" + L2_VOLTAGE_KEY,       "regex" : re.compile(b'\x77\x07\x01\x00\x34\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 1,      "unit" : "V",   "ignore" : False, "signed" : False, "description" : "instantaneousVoltageL2"    },       # "aktuelle Spannung L2"
        L3_VOLTAGE_KEY       : { "fullname" : "1-0:" + L3_VOLTAGE_KEY,       "regex" : re.compile(b'\x77\x07\x01\x00\x48\x07\x00\xFF\x01\x01\x62\x23\x52\xFF\x63(.{2})\x01',    re.MULTILINE | re.DOTALL), "resolution" : 1,      "unit" : "V",   "ignore" : False, "signed" : False, "description" : "instantaneousVoltageL3"    },       # "aktuelle Spannung L3"
        "199.130.3"          : { "fullname" : "129-129:199.130.3",           "regex" : re.compile(b'\x77\x07\x81\x81\xC7\x82\x03\xFF\x01\x01\x01\x01\x04(.{3})\x01',            re.MULTILINE | re.DOTALL), "resolution" : "dump", "unit" : "",    "ignore" : False,                   "description" : "manufacturerID"    },               # "Hersteller-ID"
        "199.130.5"          : { "fullname" : "129-129:199.130.5",           "regex" : re.compile(b'\x77\x07\x81\x81\xC7\x82\x05\xFF\x01\x01\x01\x01\x83\x02(.{48})\x01',       re.MULTILINE | re.DOTALL), "resolution" : "hex",  "unit" : "",    "ignore" : True,                    "description" : "status"    },                       # "Status"            -> the lenght of 48 is 48 characters + first length byte (0x83) with set high bit + second length byte (0x02) = line length of 50, (0x83 & 0x0F) << 4 | 0x02 = 0x32 = 50
        "199.240.6"          : { "fullname" : "129-129:199.240.6",           "regex" : re.compile(b'\x77\x07\x81\x81\xC7\xF0\x06\xFF\x01\x01\x01\x01\x04(.{3})\x01',            re.MULTILINE | re.DOTALL), "resolution" : "hex",  "unit" : "",    "ignore" : True,                    "description" : "unknown"    },                      # "unbekannt"
    }

    SECONDS_PER_HOUR = 60 * 60      # an hour has 3600 seconds
    POWER_OFF_LEVEL  = 0            # 0 watts means power OFF

    # names to be delivered to home automation
    DELIVERED_OVERALL_TEXT             = "DeliveredEnergyOverall"
    RECEIVED_OVERALL_TEXT              = "ReceivedEnergyOverall"
    CURRENT_POWER_TEXT                 = "CurrentPower"
    CURRENT_POWER_L1_TEXT              = "CurrentPowerL1"
    CURRENT_POWER_L2_TEXT              = "CurrentPowerL2"
    CURRENT_POWER_L3_TEXT              = "CurrentPowerL3"
    GRID_VOLTAGE_L1_TEXT               = "GridVoltageL1"
    GRID_VOLTAGE_L2_TEXT               = "GridVoltageL2"
    GRID_VOLTAGE_L3_TEXT               = "GridVoltageL3"
    DELIVERED_TODAY_TEXT               = "DeliveredEnergyToday"
    RECEIVED_TODAY_TEXT                = "ReceivedEnergyToday"
    DELIVERED_TODAY_STARTVALUE_TEXT    = "DeliveredEnergyStartValueToday"
    RECEIVED_TODAY_STARTVALUE_TEXT     = "ReceivedEnergyStartValueToday"
    TODAYS_DATE_TEXT                   = "EnergyStartValuesDate"

    DELIVERED_CURRENT_PERIOD_TEXT      = "PeriodDeliveredEnergyCurrent"
    RECEIVED_CURRENT_PERIOD_TEXT       = "PeriodReceivedEnergyCurrent"
    ENERGY_SURPLUS_CURRENT_PERIOD_TEXT = "PeriodEnergySurplusCurrent"
    TIMESTAMP_NEWEST_MESSAGE           = "PeriodTimeNewestMessage"


    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        # for easier interface message handling use an extra queue
        self.easyMeterInterfaceQueue = Queue()

        # all messages published by our interfaces will be sent to our one interface queue
        super().__init__(threadName, configuration, interfaceQueues = {None : self.easyMeterInterfaceQueue})


        # initialize object variables...

        # data for easy meter message to be sent out to worker thread
        self.energyData = {
            self.DELIVERED_CURRENT_PERIOD_TEXT      : None,      # newest received energy value (it could happen that after 15 minutes a damaged message has been received, in that case we have nothing to calculate, so store each received value)
            self.RECEIVED_CURRENT_PERIOD_TEXT       : None,      # newest received delivered energy value (it could happen that after 15 minutes a damaged message has been received, in that case we have nothing to calculate, so store each received value)
            self.ENERGY_SURPLUS_CURRENT_PERIOD_TEXT : None,      # surplus of energy in current period, it's positive if more energy has been delivered than received
            self.TIMESTAMP_NEWEST_MESSAGE           : None,      # timestamp when newest message has been received
        }

        # check and prepare mandatory parameters
        self.tagsIncluded(["messageInterval"], intIfy = True, optional = True, default = 60)            # 1 minute
        self.tagsIncluded(["loadCycle"],       intIfy = True, optional = True, default = 60 * 15)       # 15 minutes

        if self.configuration["loadCycle"] % self.configuration["messageInterval"] != 0:
            raise Exception(f"loadCycle has to be an integer multiple of messageInterval")

        self.removeMqttRxQueue()        # mqttRxQueue has to be removed if it's not needed!


    def threadInitMethod(self):
        self.homeAutomationValues = { self.DELIVERED_OVERALL_TEXT : 0,     self.RECEIVED_OVERALL_TEXT : 0,     self.CURRENT_POWER_TEXT : 0  , self.CURRENT_POWER_L1_TEXT : 0  , self.CURRENT_POWER_L2_TEXT : 0  , self.CURRENT_POWER_L3_TEXT : 0  , self.DELIVERED_CURRENT_PERIOD_TEXT : 0,    self.RECEIVED_CURRENT_PERIOD_TEXT : 0,    self.GRID_VOLTAGE_L1_TEXT : 0,   self.GRID_VOLTAGE_L2_TEXT : 0,   self.GRID_VOLTAGE_L3_TEXT : 0,   self.DELIVERED_TODAY_TEXT : 0,    self.RECEIVED_TODAY_TEXT : 0,    self.DELIVERED_TODAY_STARTVALUE_TEXT : 0,     self.RECEIVED_TODAY_STARTVALUE_TEXT : 0,     self.TODAYS_DATE_TEXT : -1 }
        homeAutomationUnits       = { self.DELIVERED_OVERALL_TEXT : "kWh", self.RECEIVED_OVERALL_TEXT : "kWh", self.CURRENT_POWER_TEXT : "W", self.CURRENT_POWER_L1_TEXT : "W", self.CURRENT_POWER_L2_TEXT : "W", self.CURRENT_POWER_L3_TEXT : "W", self.DELIVERED_CURRENT_PERIOD_TEXT : "Wh", self.RECEIVED_CURRENT_PERIOD_TEXT : "Wh", self.GRID_VOLTAGE_L1_TEXT : "V", self.GRID_VOLTAGE_L2_TEXT : "V", self.GRID_VOLTAGE_L3_TEXT : "V", self.DELIVERED_TODAY_TEXT : "Wh", self.RECEIVED_TODAY_TEXT : "Wh", self.DELIVERED_TODAY_STARTVALUE_TEXT : "kWh", self.RECEIVED_TODAY_STARTVALUE_TEXT : "kWh",                       }

        # send Values to a homeAutomation to get there sliders sensors selectors and switches
        self.homeAutomationTopic = self.homeAutomation.mqttDiscoverySensor(self.homeAutomationValues, unitDict = homeAutomationUnits, subTopic = "homeautomation")

        # no initial publish in that case since old values are OK if there are some already
        #self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True, enableEcho = False)


    @classmethod
    def getSmlPattern(cls):
        '''
        patterns to match messages and values (the leading greedy match ^(.*) will ensure that partial messages received at the beginning will be thrown away and only the very last message is matched)
        '''
        return re.compile(b"^(.*)(\x1b{4}\x01{4}.*?\x1b{4}.{4})(.*)", re.MULTILINE | re.DOTALL)


    @classmethod
    def processBuffer(cls, buffer : str) -> list:
        '''
        process a received message and print it in formatted way to STDOUT

        should be used for debugging and to analyze the protocol since only searching the correct values usually is much faster
        '''
        printBuffer = ""

        def recursiveListHandler(buffer : str, index : int, data : list, entries : int, recursion : int) -> int:
            nonlocal printBuffer
            INDENT = 8
            while entries:
                try:
                    entries -= 1        # one entry handled
                    if index > len(buffer) - 1:
                        Supporter.debugPrint(f"index out of range: {len(buffer)} {index} [[{buffer}]]")     # @todo rauswerfen, wenn Problem behoben
                    elementType = buffer[index]
                    length = elementType & 0x0F
                    subIndex = 1
    
                    if elementType == 0x00:
                        # ignore fill byte
                        index += subIndex
                        printBuffer += (" " * (INDENT * recursion)) + "00" + "\n"
                        continue
    
                    # extra length?            
                    if elementType & 0x80:
                        length = (length << 4) | (buffer[index + subIndex] & 0x0F)
                        subIndex += 1
    
                    if elementType & 0x70 == 0x70:
                        # list element found
                        newList = []
                        data.append(newList)
                        printBuffer += (" " * (INDENT * recursion)) + " ".join([ "{:02X}".format(char) for char in buffer[index:index + subIndex]]) + "\n"
                        index = recursiveListHandler(buffer, index + subIndex, newList, length, recursion + 1)
                    else:
                        # value element found
                        data.append(buffer[index:index + length])
                        printBuffer += (" " * (INDENT * recursion)) + " ".join([ "{:02X}".format(char) for char in buffer[index:index + length]]) + "\n"
                        index += length
                except Exception as e:
                    self.logger.error(self, f"array index our of range exception caugth: index={index} len(buffer)={len(buffer)} exception={e}")
                    raise Exception(e)
            return index

        if Base.Crc.Crc.crc16EasyMeter(buffer[:-2]) != Base.Crc.Crc.twoBytesToWord(buffer[-2:]):
            printBuffer += "invalid CRC" + "\n"

        index = 0
        printBuffer += " ".join([ "{:02X}".format(char) for char in buffer[:4]]) + "\n"
        printBuffer += " ".join([ "{:02X}".format(char) for char in buffer[4:8]]) + "\n"
        head = buffer[:8]
        tail = buffer[-8:]
        buffer = buffer[8:-8]
        data = [ head[:4], head[4:] ]

        # handle all lists in the current message
        while index < len(buffer) - 1:
            subIndex = 0
            elementType = buffer[index]
            length = elementType & 0x0F
            subIndex += 1

            if elementType == 0x00:
                # ignore fill byte
                index += subIndex
                printBuffer += "00" + "\n"
                continue

            # only list entries are allowed at top level
            if (elementType & 0x70) != 0x70:
                data = ""
                if index > 4:
                    data += hex(buffer[index - 4])
                    data += hex(buffer[index - 3])
                    data += hex(buffer[index - 2])
                    data += hex(buffer[index - 1])
                raise Exception(f"unknown element {buffer[index]} at {index}: {data}")

            # extra length?
            if elementType & 0x80:
                length = (length << 4) | (buffer[index + subIndex] & 0x0F)
                # second byte handled
                subIndex += 1

            newList = []
            data.append(newList)

            # handle rest of the current message recursively, if list ends maybe there is another one and we will come back to here with a new list entry
            printBuffer += " ".join([ "{:02X}".format(char) for char in buffer[index:index + subIndex]]) + "\n"
            index = recursiveListHandler(buffer, index + subIndex, newList, length, 1)

        printBuffer += " ".join([ "{:02X}".format(char) for char in tail[:4]]) + "\n"
        printBuffer += " ".join([ "{:02X}".format(char) for char in tail[4:]]) + "\n"
        data.append(tail[:4])
        data.append(tail[4:])


    def processReceivedMessage(self, data : str) -> str:
        '''
        Check and process a data message received from easy meter

        All received data will be filled into self.energyData
        '''
        messageError = ""
        if Base.Crc.Crc.crc16EasyMeter(data[:-2]) != Base.Crc.Crc.twoBytesToWord(data[-2:]):
            messageError = f"invalid CRC {Base.Crc.Crc.crc16EasyMeter(data[:-2]):04X} != {Base.Crc.Crc.twoBytesToWord(data[-2:]):04X}"
            self.logger.debug(self, f"invalid message from easy meter interface: {Base.Crc.Crc.crc16EasyMeter(data[:-2]):04X} != {Base.Crc.Crc.twoBytesToWord(data[-2:]):04X}, {data}")

            # following lines is for debugging only since there shouldn't be any invalid messages from our interface!
            hexString = ":".join([ "{:02X}".format(char) for char in data])     # create printable string for log message, for the case of an error
            for key in self.SML_VALUES:
                matcher = self.SML_VALUES[key]["regex"]
                match = matcher.findall(data)
                if not len(match):
                    self.logger.warning(self, f"CRC error - no match for {key} in easy meter message: {hexString}")
                elif len(match) > 1:
                    self.logger.warning(self, f"CRC error - too many matches for {key} in easy meter message: {hexString}")
                else:
                    value = str(int.from_bytes(match[0], byteorder = "big", signed = self.SML_VALUES[key]["signed"]))
                    self.logger.warning(self, f"CRC error - matched {key}={value}")
        else:
            # try to match all keys since messages always have same content, it's an error if one key hasn't been found at all or has been found twice!
            #EasyMeter.processBuffer(data)
            #Supporter.debugPrint(f"data to match {data}", color = f"{colorama.Fore.BLUE}")
            hexString = ":".join([ "{:02X}".format(char) for char in data])     # create printable string for log message, for the case of an error
            for key in self.SML_VALUES:
                matcher = self.SML_VALUES[key]["regex"]
                match = matcher.findall(data)
                if not len(match):
                    self.logger.warning(self, f"no match for {key} in easy meter message: {hexString}")
                    messageError = f"element for {key} not found"
                    break
                elif len(match) > 1:
                    self.logger.warning(self, f"too many matches for {key} in easy meter message: {hexString}")
                    messageError = f"element for {key} found {len(match)} times"
                    break
                else:
                    if not self.SML_VALUES[key]["ignore"]:
                        if self.SML_VALUES[key]["resolution"] == "hex":
                            self.energyData[key] = "".join('{:02X} '.format(x) for x in match[0]).strip()
                        elif self.SML_VALUES[key]["resolution"] == "dump":
                            self.energyData[key] = Supporter.hexCharDump(match[0], separator = "") 
                            
                            self.energyData[key] = ""
                            for x in match[0]:
                                if x <= 32 or x >= 127:    # replace non-readable ASCII values by its hex equivalent
                                    self.energyData[key] += '{:02X} '.format(x)
                                else:
                                    self.energyData[key] += chr(x) + " "
                            self.energyData[key] = self.energyData[key].strip()
                        else:
                            try:
                                intValue = "xxx"
                                value = "xxx"
                                sign = "xxx"
                                filledUpValue = "xxx"
                                intPart = "xxx"
                                decimalPart = "xxx"

                                if self.SML_VALUES[key]["resolution"] == 0:
                                    self.energyData[key] = int(self.energyData[key])
                                else:
                                    # prepare bytes to float value
                                    intValue = int.from_bytes(match[0], byteorder = "big", signed = self.SML_VALUES[key]["signed"])
                                    value = str(abs(intValue))
                                    sign = "-" if intValue < 0 else ""                                  # does the value have a sign?
                                    if self.SML_VALUES[key]["resolution"] >= len(value):
                                        filledUpValue = value.zfill(self.SML_VALUES[key]["resolution"] + 1)     # fill in leading zeros
                                    else:
                                        filledUpValue = value
                                    intPart = filledUpValue[:-self.SML_VALUES[key]["resolution"]] or "0"        # values in front of decimal point or 0 if there are none
                                    decimalPart = filledUpValue[-self.SML_VALUES[key]["resolution"]:]

                                    self.energyData[key] = float(f"{sign}{intPart}.{decimalPart}")

#                                    Supporter.debugPrint(f"\n" +
#                                                         f"key:[{key}]\n" +
#                                                         f"resolution   :[{self.SML_VALUES[key]['resolution']}]\n" + 
#                                                         f"match        :[{match}]\n" + 
#                                                         f"intValue     :[{intValue}]\n" + 
#                                                         f"sign         :[{sign}]\n" + 
#                                                         f"value        :[{value}]\n" + 
#                                                         f"filledUpValue:[{filledUpValue}]\n" + 
#                                                         f"intPart      :[{intPart}]\n" + 
#                                                         f"decimalPart  :[{decimalPart}]\n" + 
#                                                         f"data         :[{data}]\n" +
#                                                         f"float        :[{self.energyData[key]}]")
                            except Exception as e:
                                Supporter.debugPrint(f"\n" +
                                                     f"key:[{key}]\n" +
                                                     f"resolution   :[{self.SML_VALUES[key]['resolution']}]\n" + 
                                                     f"match        :[{match}]\n" + 
                                                     f"intValue     :[{intValue}]\n" + 
                                                     f"sign         :[{sign}]\n" + 
                                                     f"value        :[{value}]\n" + 
                                                     f"filledUpValue:[{filledUpValue}]\n" + 
                                                     f"intPart      :[{intPart}]\n" + 
                                                     f"decimalPart  :[{decimalPart}]\n" + 
                                                     f"data         :[{data}]")
                                raise Exception(e)
                        #Supporter.debugPrint(f"matched: {key}={self.energyData[key]}")
                    data = re.sub(matcher, b"", data)
            # data that is currently not handled, e.g. lead-in, lead-out, and maybe forgotten values
            #Supporter.debugPrint(f"finally unmatched: {data}", color = f"{colorama.Fore.BLUE}")
        return messageError


    def calculatePeriodEnergyValues(self, manipulatedTimestamp : float = None):
        '''
        To be called if a new message from EasyMeter interface has been received.
        Takes the current energy values and calculates the period information (e.g. the received and delivered energy within the last 15 minutes)
        '''
        self.energyData[self.TIMESTAMP_NEWEST_MESSAGE] = Supporter.getTimeStamp() if manipulatedTimestamp is None else manipulatedTimestamp
        self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT] = self.accumulate(
            name = "periodDeliveredEnergyAccumulator",
            value = float(self.energyData[self.DELIVERED_ENERGY_KEY]),
            period = self.configuration["loadCycle"],
            absolute = True,
            maxRefAge = self.configuration["loadCycle"],
            timeValue = manipulatedTimestamp
        )
        self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT] = self.accumulate(
            name = "periodReceivedEnergyAccumulator",
            value = float(self.energyData[self.RECEIVED_ENERGY_KEY]),
            period = self.configuration["loadCycle"],
            absolute = True,
            maxRefAge = self.configuration["loadCycle"],
            timeValue = manipulatedTimestamp
        )
        
        if self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT] is None or self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT] is None: 
            self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT]      = None
            self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT]       = None
            self.energyData[self.ENERGY_SURPLUS_CURRENT_PERIOD_TEXT] = None
        else:
            self.energyData[self.ENERGY_SURPLUS_CURRENT_PERIOD_TEXT] = self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT] - self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT]


    def receiveGridMeterMessage(self):
        '''
        Takes the newest received bytes from easy meter, adds it to current receive buffer and tries to find a valid message
        If a valid message could be found it will be processed and proper values will be set
        '''
        messageError = True
        
        # timeout timer in case no new message or only invalid messages arrive
        timeout = self.timer("periodEnergyTimeout", startTime = Supporter.getTimeOfDay(), timeout = self.configuration["loadCycle"])

        if not self.easyMeterInterfaceQueue.empty():
            while not self.easyMeterInterfaceQueue.empty():
                message = self.easyMeterInterfaceQueue.get(block = False)  # read a message from interface but take only last one (if there are more they can be thrown away, only the newest one is from interest)

                # take data out of message from easy meter interface
                data = message["content"]
                messageError = self.processReceivedMessage(data)            # fill variables from message content (if message is OK)

                if not messageError:
                    calculatePeriodEnergyValues()

                    # retrigger timeout timer
                    self.timer("periodEnergyTimeout")

        # timeout because no new easymeter message received?
        if timeout:
            self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT]      = None
            self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT]       = None
            self.energyData[self.ENERGY_SURPLUS_CURRENT_PERIOD_TEXT] = None
            

        Supporter.debugPrint(f"energy data = {self.energyData}")


    def prepareHomeAutomation(self, force : bool = False):
        # ensure all needed keys have already been prepared, otherwise return with False
        keys = [self.RECEIVED_ENERGY_KEY, self.DELIVERED_ENERGY_KEY, self.CURRENT_POWER_KEY, self.CURRENT_POWER_L1_KEY, self.CURRENT_POWER_L2_KEY, self.CURRENT_POWER_L3_KEY, self.L1_VOLTAGE_KEY, self.L2_VOLTAGE_KEY, self.L3_VOLTAGE_KEY]

        for key in keys:
            if key not in self.energyData:
                #Supporter.debugPrint(f"{key} is still missed in self.energyData!", color = "RED")
                return False

        # update values from easymeter
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_OVERALL_TEXT,          self.energyData[self.RECEIVED_ENERGY_KEY],                                   compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1, tagName = self.RECEIVED_OVERALL_TEXT         ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_OVERALL_TEXT,         self.energyData[self.DELIVERED_ENERGY_KEY],          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1, tagName = self.DELIVERED_OVERALL_TEXT        ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_TEXT,             self.energyData[self.CURRENT_POWER_KEY],             compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2, tagName = self.CURRENT_POWER_TEXT            ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L1_TEXT,          self.energyData[self.CURRENT_POWER_L1_KEY],          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2, tagName = self.CURRENT_POWER_L1_TEXT         ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L2_TEXT,          self.energyData[self.CURRENT_POWER_L2_KEY],          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2, tagName = self.CURRENT_POWER_L2_TEXT         ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L3_TEXT,          self.energyData[self.CURRENT_POWER_L3_KEY],          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2, tagName = self.CURRENT_POWER_L3_TEXT         ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_CURRENT_PERIOD_TEXT,  self.energyData[self.DELIVERED_CURRENT_PERIOD_TEXT], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5, tagName = self.DELIVERED_CURRENT_PERIOD_TEXT ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_CURRENT_PERIOD_TEXT,   self.energyData[self.RECEIVED_CURRENT_PERIOD_TEXT],  compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5, tagName = self.RECEIVED_CURRENT_PERIOD_TEXT  ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L1_TEXT,           self.energyData[self.L1_VOLTAGE_KEY],                compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1, tagName = self.GRID_VOLTAGE_L1_TEXT          ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L2_TEXT,           self.energyData[self.L2_VOLTAGE_KEY],                compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1, tagName = self.GRID_VOLTAGE_L2_TEXT          ), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L3_TEXT,           self.energyData[self.L3_VOLTAGE_KEY],                compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1, tagName = self.GRID_VOLTAGE_L3_TEXT          ), force = force)

        # update calculated values
        today = Supporter.getDate()            # today's date without time
        if self.homeAutomationValues[self.TODAYS_DATE_TEXT] != today:
            # take over current values as new start values because stored day is not today
            self.homeAutomationValues[self.RECEIVED_TODAY_STARTVALUE_TEXT]  = self.homeAutomationValues[self.RECEIVED_OVERALL_TEXT]
            self.homeAutomationValues[self.DELIVERED_TODAY_STARTVALUE_TEXT] = self.homeAutomationValues[self.DELIVERED_OVERALL_TEXT]
            self.homeAutomationValues[self.TODAYS_DATE_TEXT] = today
            changed = True
            #Supporter.debugPrint(f"changed (self.TODAYS_DATE_TEXT)", color = "LIGHTCYAN", borderSize = 5)

        changedTimerName = "changedTimer"
        changedTimerTimeout = 10

        # lambda as compare method to ensure that DELIVERED_TODAY_TEXT and RECEIVED_TODAY_TEXT is not published faster than 10 seconds
        compareWithTimer = lambda value1, value2: (value1 != value2) and (not self.timerExists(changedTimerName) or self.timer(changedTimerName))

        todayReceived  = (self.homeAutomationValues[self.RECEIVED_OVERALL_TEXT]  - self.homeAutomationValues[self.RECEIVED_TODAY_STARTVALUE_TEXT])  * 1000      # we need Wh for better comparisson
        todayDelivered = (self.homeAutomationValues[self.DELIVERED_OVERALL_TEXT] - self.homeAutomationValues[self.DELIVERED_TODAY_STARTVALUE_TEXT]) * 1000      # we need Wh for better comparisson
        todayReceivedChanged  = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_TODAY_TEXT,           todayDelivered,                                                     compareMethod = compareWithTimer, force = force)
        todayDeliveredChanged = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_TODAY_TEXT,            todayReceived,                                                      compareMethod = compareWithTimer, force = force)
        changed = changed or todayReceivedChanged or todayDeliveredChanged

        #if todayReceivedChanged:
        #    Supporter.debugPrint(f"changed (self.RECEIVED_OVERALL_TEXT)", color = "LIGHTCYAN", borderSize = 5)
        #if todayDeliveredChanged:
        #    Supporter.debugPrint(f"changed (self.DELIVERED_OVERALL_TEXT)", color = "LIGHTCYAN", borderSize = 5)

        if changed:
            # remember publish time and reset timer
            self.timer(name = changedTimerName, timeout = changedTimerTimeout, reSetup = True)

        return changed


    def threadMethod(self):
        publishedData = {}
        publishedDataResult = self.getPublishedData(publishedData = publishedData, topic = self.homeAutomationTopic, timeout = 0, failed = not self.getStartupPhase())
        if publishedDataResult != MqttBase.MQTT_READBACK.DONE:
            if publishedDataResult == MqttBase.MQTT_READBACK.RECEIVED:
                today = Supporter.getDate()            # today's date without time
                if ("content" in publishedData) and (self.TODAYS_DATE_TEXT in publishedData["content"]) and (publishedData["content"][self.TODAYS_DATE_TEXT] == today):
                    # take over the stored values, as they are still current
                    self.homeAutomationValues[self.DELIVERED_TODAY_STARTVALUE_TEXT] = publishedData["content"][self.DELIVERED_TODAY_STARTVALUE_TEXT]
                    self.homeAutomationValues[self.RECEIVED_TODAY_STARTVALUE_TEXT]  = publishedData["content"][self.RECEIVED_TODAY_STARTVALUE_TEXT]
                    self.homeAutomationValues[self.TODAYS_DATE_TEXT] = today
                else:
                    self.homeAutomationValues[self.TODAYS_DATE_TEXT] = Supporter.getDate(1, 1, 1)     # set some date in the past since stored values are too old, so current values will be used as start values
            elif not (publishedDataResult == MqttBase.MQTT_READBACK.PENDING):
                self.homeAutomationValues[self.TODAYS_DATE_TEXT] = Supporter.getDate(1, 1, 1)         # set some date in the past because there are no stored values, so current values will be used as start values
        else:
            # any grid meter data to be received?
            self.receiveGridMeterMessage()

            # one message every 60 seconds
            forceHomeAutomationUpdate = False
            if self.timer("messageTimer", timeout = self.configuration["messageInterval"], startTime = Supporter.getTimeOfToday(), firstTimeTrue = False):
                outTopic = self.createOutTopic(self.getObjectTopic())
                self.logger.debug(self, f"new message published at {outTopic}: {str(self.energyData)}")
                self.mqttPublish(outTopic, self.energyData, globalPublish = False)
                forceHomeAutomationUpdate = True

            # prepare data for homeautomation (to be sent on any value change that is outside of given threshold)
            if self.prepareHomeAutomation(force = forceHomeAutomationUpdate):
                # publish data for homeautomation if any values have changed
                self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True)


    def threadBreak(self):
        time.sleep(1)          # give other threads a chance to run and ensure that a thread which writes to the logger doesn't flood it


if __name__ == "__main__":
    TestClass = EasyMeter
    ThreadName = "EasyMeter"
    
    from Logger.Logger import Logger
    loggerConfiguration = {
        "projectName": "AccuTester",
        "homeAutomation": "HomeAutomation.HomeAssistantDiscover.HomeAssistantDiscover",
        "homeAutomationPrefix": "X1"    
    }
    TestClass.logger = Logger(threadName = "Logger", configuration = loggerConfiguration, interfaceQueues = None)

    testData = [
        bytearray(b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01v\x0bESYA\xad\xd0\x14\xe9\xe4\xfcb\x00b\x00rc\x01\x01v\x01\x04ESY\x08ESY\xa1\xaa\xe4\xfc\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01\x01c\x1e\x14\x00v\x0bESYA\xad\xd0\x14\xe9\xe4\xfdb\x00b\x00rc\x07\x01w\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x07\x01\x00b\n\xff\xffrb\x01e\x06\xf8\xa1\xaa\xf1\x00w\x07\x81\x81\xc7\x82\x03\xff\x01\x01\x01\x01\x04ESY\x01w\x07\x01\x00\x00\x00\t\xff\x01\x01\x01\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01w\x07\x01\x00\x01\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00\x1b8ou\x15\x01w\x07\x01\x00\x02\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00F\x8f\xff\rs\x01w\x07\x01\x00\x01\x08\x01\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x00\x00<\xcbd\x01w\x07\x01\x00\x01\x08\x02\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x1b82\xa9\xb1\x01w\x07\x01\x00\x10\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfchI\x01w\x07\x01\x00$\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xff\xc3e\x01w\x07\x01\x008\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe.\xc1\x01w\x07\x01\x00L\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfev$\x01w\x07\x81\x81\xc7\x82\x05\xff\x01\x01\x01\x01\x83\x02>x\xcaG\x0cd\xe2\xc9\xaa\xb8\xe0o\xd8\xa3\xear\x87\xb2\xfb\xd6He\xd8\xe2\r\xc0.\xe3\xef\xce\xc57\xc5\t*\xbf\x1f\xb7\xa5 \x04\x03|V\xd7b5q\x01w\x07\x01\x00\x00\x00\x00\xff\x01\x01\x01\x01\x0f1ESY1162827984\x01w\x07\x01\x00 \x07\x00\xff\x01\x01b#R\xffc\t\x0b\x01w\x07\x01\x004\x07\x00\xff\x01\x01b#R\xffc\t<\x01w\x07\x01\x00H\x07\x00\xff\x01\x01b#R\xffc\t0\x01w\x07\x81\x81\xc7\xf0\x06\xff\x01\x01\x01\x01\x04\x01\x07?\x01\x01\x01c\x9a$\x00v\x0bESYA\xad\xd0\x14\xe9\xe4\xfeb\x00b\x00rc\x02\x01q\x01c.?\x00\x00\x00\x1b\x1b\x1b\x1b\x1a\x02\xfe\x1c'),
        bytearray(b"\x1b\x1b\x1b\x1b\x01\x01\x01\x01v\x0bESYA\xad\xd0\x14\xe9\xe5\x1db\x00b\x00rc\x01\x01v\x01\x04ESY\x08ESY\xa1\xb5\xe5\x1d\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01\x01c\xb4\xf4\x00v\x0bESYA\xad\xd0\x14\xe9\xe5\x1eb\x00b\x00rc\x07\x01w\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x07\x01\x00b\n\xff\xffrb\x01e\x06\xf8\xa1\xb5\xf1\x00w\x07\x81\x81\xc7\x82\x03\xff\x01\x01\x01\x01\x04ESY\x01w\x07\x01\x00\x00\x00\t\xff\x01\x01\x01\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01w\x07\x01\x00\x01\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00\x1b8ou\x15\x01w\x07\x01\x00\x02\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00F\x90\x00#9\x01w\x07\x01\x00\x01\x08\x01\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x00\x00<\xcbd\x01w\x07\x01\x00\x01\x08\x02\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x1b82\xa9\xb1\x01w\x07\x01\x00\x10\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfcx\x1d\x01w\x07\x01\x00$\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xff\xc2&\x01w\x07\x01\x008\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe1J\x01w\x07\x01\x00L\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe\x84\xae\x01w\x07\x81\x81\xc7\x82\x05\xff\x01\x01\x01\x01\x83\x02>x\xcaG\x0cd\xe2\xc9\xaa\xb8\xe0o\xd8\xa3\xear\x87\xb2\xfb\xd6He\xd8\xe2\r\xc0.\xe3\xef\xce\xc57\xc5\t*\xbf\x1f\xb7\xa5 \x04\x03|V\xd7b5q\x01w\x07\x01\x00\x00\x00\x00\xff\x01\x01\x01\x01\x0f1ESY1162827984\x01w\x07\x01\x00 \x07\x00\xff\x01\x01b#R\xffc\t\x0c\x01w\x07\x01\x004\x07\x00\xff\x01\x01b#R\xffc\t:\x01w\x07\x01\x00H\x07\x00\xff\x01\x01b#R\xffc\t/\x01w\x07\x81\x81\xc7\xf0\x06\xff\x01\x01\x01\x01\x04\x01\x07?\x01\x01\x01c1F\x00v\x0bESYA\xad\xd0\x14\xe9\xe5\x1fb\x00b\x00rc\x02\x01q\x01c~R\x00\x00\x00\x1b\x1b\x1b\x1b\x1a\x02\'\x82"),
        bytearray(b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01v\x0bESYA\xad\xd0\x14\xe9\xe5>b\x00b\x00rc\x01\x01v\x01\x04ESY\x08ESY\xa1\xc0\xe5>\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01\x01c\xa9\xd4\x00v\x0bESYA\xad\xd0\x14\xe9\xe5?b\x00b\x00rc\x07\x01w\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x07\x01\x00b\n\xff\xffrb\x01e\x06\xf8\xa1\xc0\xf1\x00w\x07\x81\x81\xc7\x82\x03\xff\x01\x01\x01\x01\x04ESY\x01w\x07\x01\x00\x00\x00\t\xff\x01\x01\x01\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01w\x07\x01\x00\x01\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00\x1b8ou\x15\x01w\x07\x01\x00\x02\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00F\x90\x01:\x07\x01w\x07\x01\x00\x01\x08\x01\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x00\x00<\xcbd\x01w\x07\x01\x00\x01\x08\x02\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x1b82\xa9\xb1\x01w\x07\x01\x00\x10\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfcl2\x01w\x07\x01\x00$\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xff\xc1\x12\x01w\x07\x01\x008\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe,\x19\x01w\x07\x01\x00L\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe\x7f\x08\x01w\x07\x81\x81\xc7\x82\x05\xff\x01\x01\x01\x01\x83\x02>x\xcaG\x0cd\xe2\xc9\xaa\xb8\xe0o\xd8\xa3\xear\x87\xb2\xfb\xd6He\xd8\xe2\r\xc0.\xe3\xef\xce\xc57\xc5\t*\xbf\x1f\xb7\xa5 \x04\x03|V\xd7b5q\x01w\x07\x01\x00\x00\x00\x00\xff\x01\x01\x01\x01\x0f1ESY1162827984\x01w\x07\x01\x00 \x07\x00\xff\x01\x01b#R\xffc\t\x13\x01w\x07\x01\x004\x07\x00\xff\x01\x01b#R\xffc\t2\x01w\x07\x01\x00H\x07\x00\xff\x01\x01b#R\xffc\t2\x01w\x07\x81\x81\xc7\xf0\x06\xff\x01\x01\x01\x01\x04\x01\x07?\x01\x01\x01c\xa1w\x00v\x0bESYA\xad\xd0\x14\xe9\xe5@b\x00b\x00rc\x02\x01q\x01cr\xf2\x00\x00\x00\x1b\x1b\x1b\x1b\x1a\x02\x01\xbc'),
        bytearray(b'\x1b\x1b\x1b\x1b\x01\x01\x01\x01v\x0bESYA\xad\xd0\x14\xe9\xe4\xdbb\x00b\x00rc\x01\x01v\x01\x04ESY\x08ESY\xa1\x9f\xe4\xdb\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01\x01c\xa6\xf0\x00v\x0bESYA\xad\xd0\x14\xe9\xe4\xdcb\x00b\x00rc\x07\x01w\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x07\x01\x00b\n\xff\xffrb\x01e\x06\xf8\xa1\x9f\xf1\x00w\x07\x81\x81\xc7\x82\x03\xff\x01\x01\x01\x01\x04ESY\x01w\x07\x01\x00\x00\x00\t\xff\x01\x01\x01\x01\x0b\t\x01ESY\x11\x03\xbe\xad\xd0\x01w\x07\x01\x00\x01\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00\x1b8ou\x15\x01w\x07\x01\x00\x02\x08\x00\xffd\x00\x02\xa0\x01b\x1eR\xfcY\x00\x00\x00F\x8f\xfd\xf6\xeb\x01w\x07\x01\x00\x01\x08\x01\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x00\x00<\xcbd\x01w\x07\x01\x00\x01\x08\x02\xff\x01\x01b\x1eR\xfcY\x00\x00\x00\x1b82\xa9\xb1\x01w\x07\x01\x00\x10\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfcy\xed\x01w\x07\x01\x00$\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xff\xc4y\x01w\x07\x01\x008\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe0\xc0\x01w\x07\x01\x00L\x07\x00\xff\x01\x01b\x1bR\xfeY\xff\xff\xff\xff\xff\xfe\x84\xb5\x01w\x07\x81\x81\xc7\x82\x05\xff\x01\x01\x01\x01\x83\x02>x\xcaG\x0cd\xe2\xc9\xaa\xb8\xe0o\xd8\xa3\xear\x87\xb2\xfb\xd6He\xd8\xe2\r\xc0.\xe3\xef\xce\xc57\xc5\t*\xbf\x1f\xb7\xa5 \x04\x03|V\xd7b5q\x01w\x07\x01\x00\x00\x00\x00\xff\x01\x01\x01\x01\x0f1ESY1162827984\x01w\x07\x01\x00 \x07\x00\xff\x01\x01b#R\xffc\t\x13\x01w\x07\x01\x004\x07\x00\xff\x01\x01b#R\xffc\t<\x01w\x07\x01\x00H\x07\x00\xff\x01\x01b#R\xffc\t0\x01w\x07\x81\x81\xc7\xf0\x06\xff\x01\x01\x01\x01\x04\x01\x07?\x01\x01\x01cO{\x00v\x0bESYA\xad\xd0\x14\xe9\xe4\xddb\x00b\x00rc\x02\x01q\x01c\x17#\x00\x00\x00\x1b\x1b\x1b\x1b\x1a\x02\xdc%'),
    ]

    configuration = {}
    testObject = TestClass(threadName = ThreadName, configuration = configuration)
    
    #TestClass.classVar = "foo"
    #testObject.objectVar = "bar"
    testObject.threadInitMethod()

    # inject a valid message
    testObject.processReceivedMessage(testData[0])
    testObject.calculatePeriodEnergyValues()
    deliveredAccu = testObject._getAccumulator("periodDeliveredEnergyAccumulator")
    receivedAccu  = testObject._getAccumulator("periodReceivedEnergyAccumulator")

    import random
    timeStamp = testObject.energyData[testObject.TIMESTAMP_NEWEST_MESSAGE]
    for turn in range(1,20):
        timeStamp += 3*60           # 3 minutes later...
        testObject.energyData[testObject.DELIVERED_ENERGY_KEY] += 1.2           # 1.2 kWh more...
        testObject.calculatePeriodEnergyValues(manipulatedTimestamp  = timeStamp)
        received = testObject.energyData[testObject.RECEIVED_CURRENT_PERIOD_TEXT]
        delivered = testObject.energyData[testObject.DELIVERED_CURRENT_PERIOD_TEXT]   
        

    ####timeValue = 1
    ####for turn in range(1,20):
    ####    #result = testObject.accumulate("foo", round(random.uniform(0, 3), 2), period = 4, timeValue = timeValue)
    ####    #result = testObject.accumulate("foo", turn, period = 4, timeValue = timeValue)     # sum up last 4 entries
    ####    #result = testObject.accumulate("foo", turn, period = 4, maxRefAge = 1.5, timeValue = timeValue)     # sum up last 4 entries
    ####    #result = testObject.accumulate("foo", turn, absolute = True, period = 4, timeValue = timeValue)
    ####    #result = testObject.accumulate("foo", turn * 2, absolute = True, period = 8, timeValue = timeValue * 2)
    ####    #result = testObject.accumulate("foo", turn * 2, absolute = True, multiplyTime = True, period = 8, timeValue = timeValue * 2)
    ####    result = testObject.accumulate(name = "foo", value = turn * 2, period = 8, absolute = True, multiplyTime = True, maxRefAge = 1.5, timeValue = timeValue * 2)
    ####    print(result)
    ####
    ####    timeValue += 1
    ####
    ####    if turn == 5:
    ####        timeValue += 5

