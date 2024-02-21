import time
import serial    #pip install pyserial
import re
import json
from Base.Supporter import Supporter

from Base.InterfaceBase import InterfaceBase


class BasicUartInterface(InterfaceBase):
    '''
    classdocs
    '''

    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.tagsIncluded(["interface"])
        self.tagsIncluded(["baudrate"], intIfy = True)

        self.tagsIncluded(["bytesize"], optional = True, default = serial.EIGHTBITS)
        self.tagsIncluded(["parity"], optional = True, default = serial.PARITY_NONE)
        self.tagsIncluded(["stopbits"], optional = True, default = serial.STOPBITS_ONE)
        self.tagsIncluded(["timeout"], optional = True, default = 4)
        self.tagsIncluded(["xonxoff"], optional = True, default = False)
        self.tagsIncluded(["rtscts"], optional = True, default = False)
        self.tagsIncluded(["writeTimeout"], optional = True, default = 4)

        self.receivedData = b""


    def reInitSerial(self):
        success = True
        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            self.serialClose()
            self.serialConn.open()
        except Exception as exception:
            self.logger.error(self, f"Serial Port {self.name} reInit failed: {exception}")
            success = False
            if self.timer(name = "timeoutReinit", timeout = 10*60):
                raise Exception("Tried to reinit serial port since 10 min. Give up!")
        if success and self.timerExists("timeoutReinit"):
            self.timer(name = "timeoutReinit", remove = True)
        return success


    def serialInit(self):
        self.serialConn = serial.Serial(
            port         = self.configuration["interface"],
            baudrate     = self.configuration["baudrate"],
            bytesize     = self.configuration["bytesize"],
            parity       = self.configuration["parity"],
            stopbits     = self.configuration["stopbits"],
            timeout      = self.configuration["timeout"],
            xonxoff      = self.configuration["xonxoff"],
            writeTimeout = self.configuration["writeTimeout"],
            rtscts       = self.configuration["rtscts"]
        )


    def serialClose(self):
        self.serialConn.close()


    def serialWrite(self, data):
        success = True
        try:
            self.serialConn.write(data)
        except Exception as exception:
            self.logger.error(self, f"Sending serial data failed: {exception}")
            success = False
            self.reInitSerial()
        return success


    def serialReadLine(self):
        '''
        Reads data up to a new line
        Don't mix serialRead() and serialReadLine()
        
        @return    
        '''
        try:
            retVal = self.serialConn.readline()
        except:
            self.reInitSerial()
            retVal = b""
        return retVal


    def flush(self, dump : bool = False):
        '''
        Read serial once, then clear receive and transmit buffers

        @param dump         usually for debugging, the receive buffer will be printed to the screen to see what is still in the buffer after the requested message has already been taken out
        '''
        try:
            if self.serialConn.inWaiting():
                self.receivedData += self.serialConn.read(self.serialConn.inWaiting())
    
            self.serialReset_input_buffer()
            self.serialReset_output_buffer()
    
            if dump:
                Supporter.debugPrint(f"serial dump [{Supporter.hexCharDump(self.receivedData, ' ')}]")
        except Exception as exception:
            self.logger.warning(self, f"Exception caught in flush method: {exception}")

        self.receivedData = b""


    def serialRead(self, length : int = 0, regex : bytes = None, timeout : int = None, dump : bool = False):
        '''
        Reads data from serial until length bytes have been received or timeout has been reached
        Don't mix serialRead() and serialReadLine()

        @param length       amount of bytes to be received, 0 = read only once up to timeout, n = read until this amount of bytes have been received
        @param regex        regex the received data has to match with, length is not supported if regex has been given, a given length will be ignored in that case
                            serialReadLine() can be simulated by serialRead(regex = b"\n$"), and thus serialReadLine() supporting different line endings can also be "simulated", e.g. serialRead(regex = b"\r$") or serialRead(regex = b"\t$")
        @param timeout      seconds to read from serial, None = use default timeout, n = read up to n seconds, 0 or negative value = read once then stop reading
        @param dump         usually for debugging, the receive buffer will be printed to the screen to see what is still in the buffer after the requested message has already been taken out

        @return             received byte string is given back except if regex has been given a match result will be given back
        '''
        returnData = b""

        if timeout is None:
            timeout = self.configuration["timeout"]

        startTime = Supporter.getTimeStamp()

        if dump:
            Supporter.debugPrint([f"serial pre dump [{Supporter.hexCharDump(self.receivedData)}]", f"length = [{length}]", f"regex = [{regex}]", f"timeout = [{timeout}]"])

        try:
            while True:
                if bytesWaiting := self.serialConn.inWaiting():
                    self.receivedData += self.serialConn.read(bytesWaiting)

                    if regex is not None:
                        if match := re.search(regex, self.receivedData, flags = re.MULTILINE | re.DOTALL):
                            #Supporter.debugPrint(f"serialRead matched ({Supporter.getSecondsSince(startTime)}s) [{match.group()}]")
                            returnData = match
                            self.receivedData = re.sub(regex, b"", self.receivedData, 1, flags = re.MULTILINE | re.DOTALL)  # remove matched string from received data buffer
                            break       # leave loop since data has been matched
                    elif len(self.receivedData) >= length:
                        if length:
                            # only send first "length" bytes, rest stays in received data until read is called again or flush has been called
                            returnData = self.receivedData[:length]
                            self.receivedData = self.receivedData[length:]
                        else:
                            # send all data
                            returnData = self.receivedData
                            self.receivedData = b""
                        #Supporter.debugPrint(f"serialRead read ({Supporter.getSecondsSince(startTime)}s) [{returnData}]")
                        break       # leave loop since data has been found

                # if timeout is <= 0, no length and no regex has been given, leave loop after first read without debug log
                if timeout <= 0 and not length and regex is None:
                    break       # leave loop because of single read
                elif Supporter.getSecondsSince(startTime) > timeout:
                    # if timeout has been given check if time is over (this works also if timeout was 0 and self.configuration["timeout"] was also 0)
                    self.logger.debug(self, f"timeout {len(self.receivedData)} {timeout} {self.receivedData}")
                    break       # leave loop because of timeout
        except Exception as exception:
            self.logger.warning(self, f"Exception caught in serialRead method: {exception}, re-init serial")
            self.reInitSerial()

        if dump:
            Supporter.debugPrint([f"serial post dump (after {Supporter.getSecondsSince(startTime):.3f}s) [{Supporter.hexCharDump(self.receivedData)}]", f"read/matched data [{returnData}]"])

        return returnData


    def serialReset_input_buffer(self):
        try: 
            self.serialConn.reset_input_buffer()
        except Exception as exception:
            self.logger.error(self, f"Could not reset_input_buffer from serial {self.name}, Error: {exception}")


    def serialReset_output_buffer(self):
        try:
            self.serialConn.reset_output_buffer()
        except Exception as exception:
            self.logger.error(self, f"Could not reset_output_buffer from serial {self.name}, Error: {exception}")


    def threadInitMethod(self):
        tries = 0
        while tries < self.MAX_INIT_TRIES:
            try:
                self.serialInit()
                break
            except Exception as exception:
                time.sleep(2)
                self.logger.error(self, f'Serial connection --{self.configuration["interface"]}-- init. {tries + 1} of {self.MAX_INIT_TRIES} failed. Error:{exception}')
            tries += 1
        if tries >= self.MAX_INIT_TRIES:
            raise Exception(f'Serial connection --{self.configuration["interface"]}-- could not established')
        self.logger.info(self, f'Serial connection --{self.configuration["interface"]}-- initialized.')

    #def threadMethod(self):


    def threadBreak(self):
        time.sleep(0.1)


    def threadTearDownMethod(self):
        self.serialClose()

