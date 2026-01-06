import time
from datetime import datetime
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger
from Worker.Worker import Worker
from Base.Supporter import Supporter
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
    DELIVERED_OVERALL_TEXT         = "DeliveredEnergyOverall"
    RECEIVED_OVERALL_TEXT          = "ReceivedEnergyOverall"
    CURRENT_POWER_TEXT             = "CurrentPower"
    CURRENT_POWER_L1_TEXT          = "CurrentPowerL1"
    CURRENT_POWER_L2_TEXT          = "CurrentPowerL2"
    CURRENT_POWER_L3_TEXT          = "CurrentPowerL3"
    DELIVERED_LAST_15_MINUTES_TEXT = "DeliveredEnergyLast15Minutes"
    RECEIVED_LAST_15_MINUTES_TEXT  = "ReceivedEnergyLast15Minutes"
    GRID_VOLTAGE_L1_TEXT           = "GridVoltageL1"
    GRID_VOLTAGE_L2_TEXT           = "GridVoltageL2"
    GRID_VOLTAGE_L3_TEXT           = "GridVoltageL3"

    def __init__(self, threadName : str, configuration : dict, interfaceQueues : dict = None):
        '''
        Constructor
        '''
        # for easier interface message handling use an extra queue
        self.easyMeterInterfaceQueue = Queue()
        
        # all messages published by our interfaces will be sent to our one interface queue
        super().__init__(threadName, configuration, interfaceQueues = {None : self.easyMeterInterfaceQueue})


        # initialize object variables...
        # dictionary to hold process data that are used to decide if and how much power can be used to load the batteries
        self.energyProcessData = {
            "currentEnergyLevel"     : 0,       # amount of collected energy within the last 15 minutes
            "lastEnergyLevel"        : 0,       # amount of collected energy within the 15 minutes before 
            "currentEnergyTimestamp" : 0,       # time stamp when the last energy message has been received (for grid loss detection)
            "messageTimestamp"       : 0,       # time when last message with surplus energy information has been sent out
            "gridLossDetected"       : True,    # set to be True when a grid loss has been detected (that is when started up or when seconds since last energy message is more than "gridLossThreshold")
        }

        # data for easy meter message to be sent out to worker thread
        self.energyData = {
            "validMessages"              : 0,      # we need an initial value here, otherwise "+= 1" will fail!
            "invalidMessages"            : 0,      # we need an initial value here, otherwise "+= 1" will fail!
            "lastInvalidMessageTimeStamp": 0,      # time last invalid message has been detected
            "invalidMessageError"        : 0,      # reason why the last message has been detected as invalid, e.g. "invalid CRC", "value not found", "value found twice"

            "allowedPower"               : 0,      # allowed power to be taken from the grid to load the batteries (inverter thread has to calculate proper current with known battery voltage)
            "allowedReduction"           : 0,      # allowed reduction used for allowed power level (has already been subtracted from allowedPoer!)
            "allowedTimestamp"           : 0,      # time stamp when allowed power has been set for the first time

            "previousPower"              : 0,      # previous allowed power, for logging
            "previousReduction"          : 0,      # reduction used for previous power level (has already been subtracted!)
            "previousTimestamp"          : 0,      # time stamp when the previous power has been taken

            "updatePowerValue"           : False,  # set to True in the one message every "loadCycle" seconds to inform the worker thread that an update should be done now 
        }

        # check and prepare mandatory parameters
        self.tagsIncluded(["loadCycle", "gridLossThreshold", "decreasingDelta", "increasingDelta", "minimumPowerStep"], intIfy = True)

        self.tagsIncluded(["messageInterval"], intIfy = True, optional = True, default = 60)

        if (self.configuration["loadCycle"] // self.configuration["messageInterval"]) <= 1:
            raise Exception(f"loadCycle must to be larger than messageInterval =={self.configuration['messageInterval']}") 

        if ((self.configuration["loadCycle"] // self.configuration["messageInterval"]) * self.configuration["messageInterval"]) != self.configuration["loadCycle"]:  
            raise Exception(f"loadCycle has to be an integer multiple of messageInterval")

        if self.configuration["loadCycle"] <= (4 * self.configuration["gridLossThreshold"]):
            raise Exception(f"loadCycle has to be at least 4 times gridLossThresold")

        if self.configuration["gridLossThreshold"] <= 0:
            raise Exception(f"gridLossThresold must be larger than 0 seconds")

        if self.configuration["minimumPowerStep"] < 100:
            raise Exception(f"minimumPowerStep must be at least 100 watts")


    def threadInitMethod(self):
        self.homeAutomationValues = { self.DELIVERED_OVERALL_TEXT : 0,     self.RECEIVED_OVERALL_TEXT : 0,     self.CURRENT_POWER_TEXT : 0  , self.CURRENT_POWER_L1_TEXT : 0  , self.CURRENT_POWER_L2_TEXT : 0  , self.CURRENT_POWER_L3_TEXT : 0  , self.DELIVERED_LAST_15_MINUTES_TEXT : 0,    self.RECEIVED_LAST_15_MINUTES_TEXT : 0,    self.GRID_VOLTAGE_L1_TEXT : 0,   self.GRID_VOLTAGE_L2_TEXT : 0,   self.GRID_VOLTAGE_L3_TEXT : 0   }
        homeAutomationUnits       = { self.DELIVERED_OVERALL_TEXT : "kWh", self.RECEIVED_OVERALL_TEXT : "kWh", self.CURRENT_POWER_TEXT : "W", self.CURRENT_POWER_L1_TEXT : "W", self.CURRENT_POWER_L2_TEXT : "W", self.CURRENT_POWER_L3_TEXT : "W", self.DELIVERED_LAST_15_MINUTES_TEXT : "Wh", self.RECEIVED_LAST_15_MINUTES_TEXT : "Wh", self.GRID_VOLTAGE_L1_TEXT : "V", self.GRID_VOLTAGE_L2_TEXT : "V", self.GRID_VOLTAGE_L3_TEXT : "V" }
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


    def handleReceivedValues(self, messageError : bool):
        '''
        Check result from processed data and fill in proper values or store error information
        '''
        newPowerLevelAvailable = False

        if not messageError:
            self.energyData["validMessages"] += 1

            self.logger.debug(self, str(self.energyData))

            # current energy level == 0 means script has been (re-)started and we are here for the first time, in that case take the values received with the last message
            if self.energyProcessData["currentEnergyLevel"] == 0:              # can only happen after reboot since this is the real overall energy measured so far
                self.energyProcessData["lastEnergyLevel"] = 0
                self.energyProcessData["collectedEnergy"] = 0

            # collect new delivered energy value and check if specified cycle time is over
            if (accumulated := self.accumulator(name = "collectedEnergyForTheLast15Minutes",
                                                power = float(self.energyData[self.DELIVERED_ENERGY_KEY]),
                                                timeout = self.configuration["loadCycle"],
                                                synchronized = True,
                                                absolute = True,
                                                autoReset = True,
                                                minMaxAverage = True)) is not None:
                newPowerLevelAvailable = True                                                                      # inform caller that new surplus data is available
                self.energyProcessData["lastEnergyLevel"]    = self.energyProcessData["currentEnergyLevel"]        # backup last level
                self.energyProcessData["currentEnergyLevel"] = accumulated["acc"]                                  # remember new level

            # remember current time for grid loss detection
            self.energyProcessData["currentEnergyTimestamp"] = Supporter.getTimeStamp()
        else:
            # logging values only
            self.energyData["invalidMessages"]            += 1
            self.energyData["lastInvalidMessageTimeStamp"] = Supporter.getTimeStamp()
            self.energyData["invalidMessageError"]         = messageError

        return newPowerLevelAvailable


    def receiveGridMeterMessage(self):
        '''
        Takes the lastly received bytes from easy meter, adds it to current receive buffer and tries to find a valid message
        If a valid message could be found it will be processed and proper values will be set
        '''
        #Supporter.debugPrint(f"{watching...")

        newPowerLevelAvailable = False

        if not self.easyMeterInterfaceQueue.empty():
            while not self.easyMeterInterfaceQueue.empty():
                message = self.easyMeterInterfaceQueue.get(block = False)  # read a message from interface but take only last one (if there are more they can be thrown away, only the newest one is from interest)
    
                # take data out of message from easy meter interface
                data = message["content"]
                messageError = self.processReceivedMessage(data)            # fill variables from message content (if message is OK)
                newPowerLevelAvailable = newPowerLevelAvailable or self.handleReceivedValues(messageError)                     # process filled variables and try to calculate new power level

            #Supporter.debugPrint(f"energy data = {self.energyData}")
            #Supporter.debugPrint(f"energy process data = {self.energyProcessData}")

        return newPowerLevelAvailable


    def calculateNewPowerLevel(self):
        '''
        Calculate new power level from last and current energy values
        '''
        # handle grid loss if necessary, otherwise calculate new power levels
        if self.energyProcessData["gridLossDetected"]:
            # grid loss handling (set back initial values)
            newReductionLevel  = self.configuration["decreasingDelta"]
            newPowerLevel      = self.POWER_OFF_LEVEL
        else:
            # grid is OK so send proper values
            lastEnergyDelta    = int(self.energyProcessData["lastEnergyLevel"])
            currentEnergyDelta = int(self.energyProcessData["currentEnergyLevel"])
            if lastEnergyDelta > currentEnergyDelta:
                newReductionLevel = self.configuration["decreasingDelta"]
            else:
                newReductionLevel = self.configuration["increasingDelta"]
            newPowerLevel      = currentEnergyDelta / (self.SECONDS_PER_HOUR / self.configuration["loadCycle"]) - newReductionLevel            # 1 hour / "loadCycle" to calculate power from energy! This is ok even for the first cycle that can be a bit shorter since in that case less energy will be calculated than really collected

            # no negative power level but with reduction level this can happen!
            if newPowerLevel < self.POWER_OFF_LEVEL:
                newPowerLevel = self.POWER_OFF_LEVEL

        return (newPowerLevel, newReductionLevel)


    def prepareNewEasyMeterMessage(self):
        '''
        Should be called every "loadCycle" seconds (synchronized to quarter hours)

        Checks if grid loss has been detected and calculates new power value for the message to the worker thread
        '''
        # calculate new power level and reduction value
        (newPowerLevel, newReductionLevel) = self.calculateNewPowerLevel()

        # do we have to switch OFF -or- difference between current and last set power level large enough?
        messageTime = Supporter.getTimeStamp()
        if (newPowerLevel == self.POWER_OFF_LEVEL) or (Supporter.absoluteDifference(newPowerLevel, self.energyData["allowedPower"]) >= self.configuration["minimumPowerStep"]): 
            # copy current values over to previous ones
            self.energyData["previousPower"]     = self.energyData["allowedPower"]
            self.energyData["previousReduction"] = self.energyData["allowedReduction"]
            self.energyData["previousTimestamp"] = self.energyData["allowedTimestamp"]

            # fill in new current values
            self.energyData["allowedPower"]     = newPowerLevel         # maximum allowed power taken from grid to load accumulator                                  
            self.energyData["allowedReduction"] = newReductionLevel     # published for informational reasons only since the power has already limited by this amount
            self.energyData["allowedTimestamp"] = messageTime           # remember time of last set power level (since not every "loadCycle" a new level is set! 

            # tag this message as message with new power level
            self.energyData["updatePowerValue"] = True

        # remember time last message has been created
        self.energyProcessData["messageTimestamp"] = messageTime    

        # reset some values for the next turn
        self.energyProcessData["gridLossDetected"] = False                  # reset grid loss detection for next cycle


    def prepareHomeAutomation(self, force : bool = False):
        # ensure all needed keys have already been prepared, otherwise return with False
        keys = [self.RECEIVED_ENERGY_KEY, self.DELIVERED_ENERGY_KEY, self.CURRENT_POWER_KEY, self.CURRENT_POWER_L1_KEY, self.CURRENT_POWER_L2_KEY, self.CURRENT_POWER_L3_KEY, self.L1_VOLTAGE_KEY, self.L2_VOLTAGE_KEY, self.L3_VOLTAGE_KEY]

        for key in keys:
            if key not in self.energyData:
                #Supporter.debugPrint(f"{key} is still missed in self.energyData!", color = "RED")
                return False

        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_OVERALL_TEXT,          self.energyData[self.RECEIVED_ENERGY_KEY],                          compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_OVERALL_TEXT,         self.energyData[self.DELIVERED_ENERGY_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_TEXT,             self.energyData[self.CURRENT_POWER_KEY],    compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L1_TEXT,          self.energyData[self.CURRENT_POWER_L1_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L2_TEXT,          self.energyData[self.CURRENT_POWER_L2_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.CURRENT_POWER_L3_TEXT,          self.energyData[self.CURRENT_POWER_L3_KEY], compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 2), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.DELIVERED_LAST_15_MINUTES_TEXT, 0,                                          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)        # @todo sinnvollen Wert einfüllen!
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.RECEIVED_LAST_15_MINUTES_TEXT,  0,                                          compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 5), force = force)        # @todo sinnvollen Wert einfüllen!
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L1_TEXT,           self.energyData[self.L1_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L2_TEXT,           self.energyData[self.L2_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
        changed = Supporter.compareAndSetDictElement(self.homeAutomationValues, self.GRID_VOLTAGE_L3_TEXT,           self.energyData[self.L3_VOLTAGE_KEY],       compareValue = changed, compareMethod = functools.partial(Supporter.deltaOutsideRange, percent = 1), force = force)
        return changed


    def threadMethod(self):
        '''
        first loop:
            self.energyProcessData["gridLossDetected"] = True
       
        every loop run:
            "lastEnergyLevel" == 0:
                fill in current energy level (overall first cycle is probably a "shorter" one but that doesn't matter)
            time since last time > 2 minutes -> error (probably grid loss):
                self.energyProcessData["gridLossDetected"] = True

        every minute a message is sent out:
            containing all data, some data could be unchanged, others will be new

        every event time:
            self.energyProcessData["gridLossDetected"] = False
            self.energyProcessData["currentEnergyTimestamp"] = now
            store new power level
            send signal message (in case of real grid loss nth. will happen but in case it's a bug and there is no grid loss a message will be sent!

        1st cycle is a grid loss one
        2nd cycle is probably a shorter one (since timer is synchronized to quarter hours the 2nd cycle length depends on start time related to next quarter hour)
        3rd... cycles are common ones
        '''
        # read messages from project (not from EasyMeterInterface!!!)
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.debug(self, "received message :" + str(newMqttMessageDict))

        # grid loss detected?
        if Supporter.getSecondsSince(self.energyProcessData["currentEnergyTimestamp"]) > self.configuration["gridLossThreshold"]:
            self.energyProcessData["gridLossDetected"] = True

        # any grid meter data to be received?
        if self.receiveGridMeterMessage():
            # prepare the one message every "loadCycle" seconds that contains new power values
            self.prepareNewEasyMeterMessage()

        # one message every 60 seconds
        forceHomeAutomationUpdate = False
        if self.timer("messageTimer", timeout = self.configuration["messageInterval"], startTime = Supporter.getTimeOfToday(), firstTimeTrue = False):
            outTopic = self.createOutTopic(self.getObjectTopic())
            self.logger.debug(self, f"new message published at {outTopic}: {str(self.energyData)}")
            self.mqttPublish(outTopic, self.energyData, globalPublish = False)
            self.energyData["updatePowerValue"] = False     # set to False (again) for all following messages until it has been decided to set a new power level
            forceHomeAutomationUpdate = True

        # prepare data for homeautomation (to be sent on any value change that is outside of given threshold)
        if self.prepareHomeAutomation(force = forceHomeAutomationUpdate):
            # publish data for homeautomation if any values have changed
            self.mqttPublish(self.homeAutomationTopic, self.homeAutomationValues, globalPublish = True)
            #Supporter.debugPrint(f"published to {self.homeAutomationTopic} [{self.homeAutomationValues}]")


    def threadBreak(self):
        time.sleep(1)          # give other threads a chance to run and ensure that a thread which writes to the logger doesn't flood it


