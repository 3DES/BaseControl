import time
import serial    #pip install pyserial
import re
import json
from Base.Supporter import Supporter

from Base.InterfaceBase import InterfaceBase
from Interface.Uart.BasicUartInterface import BasicUartInterface


class SLCanUartInterface(BasicUartInterface):
    '''
    classdocs
    
    https://github.com/normaldotcom/canable2-fw/blob/main/README.md
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.VALID_BAUD_RATES = [10000, 20000, 50000, 100000, 125000, 250000, 500000, 750000, 1000000, 83300]   # position is important for command, 10000 = S0, 20000 = S1, ...!!!
        if self.configuration["baudrate"] not in self.VALID_BAUD_RATES:
            raise Exception(f"given baud rate {self.configuration['baudrate']} is not supported")


    def reInitSerial(self):
        success = super().reInitSerial()
        success = self.serialWrite("O") and success
        success = self.serialWrite(f"S{self.VALID_BAUD_RATES.index(self.configuration['baudrate'])}") and success
        return success


    def readFrame(self, address : int = None, timeout : int = None, dump : bool = False):
        '''
        Reads from serial and matches the result so each telegram part can be taken from the match without further searching

        @param address    address can be given but if telegram has different address it's not a match!
        @param timeout    see self.serialRead()
        @param dump       see self.serialRead()
        @return           dictionary with elements "datatype", "address", "length", "command", and "data"
                          or b"" in case of timeout or no-match
        '''
        #(R)([0-9A-Z]{{8}})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(T)([0-9A-Z]{{8}})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(r)([0-9A-Z]{{3}})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(t)([0-9A-Z]{{3}})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #
        #(R)({address:08X})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(T)({address:08X})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(r)({address:03X})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        #(t)({address:03X})([0-9A-Z])([0-9A-Z]{4})([0-9A-Z]*)\r
        if address is not None:
            if address < pow(2, 11):
                # address length can be 11 or 29 bits
                # groups:       12     3               2     3               4         5              6
                regex = bytes(f"(([RT])({address:08X})|([rt])({address:03X}))([0-9A-Z])([0-9A-Z]{{4}})([0-9A-Z]*)\r", 'utf-8')
            else:
                # address length can only be 29 bits
                # groups:       12     3               4         5              6
                regex = bytes(f"(([RT])({address:08X}))([0-9A-Z])([0-9A-Z]{{4}})([0-9A-Z]*)\r", 'utf-8')
        else:
            # address length can be 11 or 29 bits
            # groups:       12     3               2     3               4         5              6
            regex = bytes(f"(([RT])([0-9A-Z]{{8}})|([rt])([0-9A-Z]{{3}}))([0-9A-Z])([0-9A-Z]{{4}})([0-9A-Z]*)\r", 'utf-8')
        if telegram := self.serialRead(regex = regex, timeout = self.POLLING_TIMEOUT, dump = dump):
            return {
                "dataType" : telegram[2],   # t,r,T,R
                "address"  : telegram[3],   # 11 or 29 bit address as string
                "length"   : telegram[4],   # length as string 0..8
                "command"  : telegram[5],   # command as hex string
                "data"     : telegram[6],   # data as hex string
                }
        else:
            return telegram     # telegram is anything even if the "if" is False, then telegram is None or b"" or so...


    def serialWrite(self, data):
        '''
        Each command do a SLCAN device needs a final CR
        '''
        super().serialWrite(bytes(data + "\r", 'utf-8'))


    def serialClose(self):
        '''
        Close CAN connection of SLCAN device before closing interface
        '''
        self.serialWrite("C")
        super().serialClose()


    def serialInit(self):
        super().serialInit()
        self.serialWrite(f"S{self.VALID_BAUD_RATES.index(self.configuration['baudrate'])}")
        self.serialWrite("O")


    def sendFrame(self, command : str, address : int = 0, data : str = ""):
        '''
        @param command     Meanwell NPB command to be sent
        @param data        hexadecimal data string to be sent
                           in case of no data has been given
        @param address     address of Meanwell NPB device
        '''
        if command is None:
            raise Exception(f"no command string given")
        if len(command) < 4:
            raise Exception(f"command string [{command}] has to have length of 4")
        
        if data is None:
            data = ""
        if len(data) % 2:
            raise Exception(f"given data string [{data}] length must be dividable by 2")

        if address < pow(2, 11) and address >= 0:
            #sendString = "t" if len(data) else "r"    # not working with Meanwell!!!
            sendString = "t"    # 'r' cannot be used since Meanwell needs at least the command what means there's always a minimum of 2 data bytes!
            addressString = f"{address:03X}"            # 11 bit address
        elif address < pow(2, 29) and address >= 0:
            #sendString = "T" if len(data) else "R"    # not working with Meanwell!!!
            sendString = "T"    # 'R' cannot be used since Meanwell needs at least the command what means there's always a minimum of 2 data bytes!
            addressString = f"{address:08X}"            # 29 bit address
        else:
            raise Exception(f"given address [{address}] is not supported, 0 <= address <= {pow(2, 29)-1:08X}")
        sendString += addressString

        sendString += f"{(len(command) + len(data)) // 2}"
        sendString += command
        sendString += data

        self.serialWrite(sendString)

