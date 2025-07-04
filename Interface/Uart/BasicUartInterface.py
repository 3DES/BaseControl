import time
import serial    #pip install pyserial
import re
import json
import subprocess
import os
import sys
import pathlib

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
        self.tagsIncluded(["rebind"], optional = True, default = False)
        self._rebindBreak = .5    # time unbind and bind is allowed to take

        self.receivedData = b""
        self.tagsIncluded(["autoDump"], optional = True, default = False)


    def _buildDeviceTree(self, path: str):
        """
        Create driver tree from given interface
        """
        regex = re.compile(r'(.+)\/([^\/]+)$')
        driverTree = []
        while(found := regex.search(path)):
            device = found.group(2)
            driverPath = path
            # be patient with the trailing "/", they are very important if the path is a symbolic link!
            if os.path.exists(driverPath + "/driver/bind"):
                driverPath = str(pathlib.Path(driverPath + "/driver/").resolve())
                driverTree.append([driverPath + "/", device])
                if not re.search(r":", device):
                    # a device with a colon in its name is only an interface of a device, re-binding it is probably a good idea
                    # the first device without a colon in its name when stepping up through the device tree is the real device, re-binding it is probably also a good idea
                    # but then we should stop since re-binding all the devices when stepping up through the device tree will re-bind devices we won't re-bind, e.g. USB hubs
                    break
            path = regex.sub(r'\1', path)
        return driverTree


    def reInitSerial(self):
        success = True

        try:
            self.logger.debug(self, f"Serial Port {self.name} reInit!")
            # if "rebind" has been given try to rebind the device in case of an error
            if self.configuration["rebind"]:
                driverTree = self._buildDeviceTree(self.devicePath)
                self.logger.info(self, f"Rebinding {driverTree}")
                for driverPath, deviceName in driverTree:
                    self.serialClose()
                    driverFile = open(driverPath + "unbind", "w")
                    driverFile.write(deviceName)
                    driverFile.close()
                    time.sleep(self._rebindBreak)
                    driverFile = open(driverPath + "bind", "w")
                    driverFile.write(deviceName)
                    driverFile.close()
                    time.sleep(self._rebindBreak)
                    try:
                        self.serialConn.open()
                    except Exception as exception:
                        self.logger.info(self, f"Rebinding of {deviceName} failed")
                    else:
                        self.logger.info(self, f"Rebinding of {deviceName} succeeded")
                        break
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


    def _getUdev(self, interface : str) -> str:
        """
        Get path of a device
        """
        udevResult = "/sys" + subprocess.Popen(f"udevadm info -q all -n {interface} | grep DEVPATH | cut -d'=' -f2", shell=True, stdout=subprocess.PIPE).stdout.read().decode("utf-8").rstrip()
        if not os.path.exists(udevResult):
            message = f"udevadm info -q all -n {interface} failed with {udevResult}"
            self.logger.error(self, message)
            raise Exception(message)
        return udevResult


    def serialInit(self):
        # get device path since that's the interesting path in case of lost usb devices (it's worth a try to bring it back with unbind and bind)
        if self.configuration["rebind"]:
            self.devicePath = self._getUdev(self.configuration['interface'])
            self.logger.info(self, f"device path is {self.devicePath}")

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


    def serialWrite(self, data, dump : bool = False):
        success = True
        try:
            self.serialConn.write(data)
        except Exception as exception:
            self.logger.error(self, f"Sending serial data failed: {exception}")
            success = False
            self.reInitSerial()

        if dump or self.configuration['autoDump']:
            Supporter.debugPrint([f"::serialWrite:: serial dump [{Supporter.hexCharDump(data)}]", f"read/matched data [{data}]", f"reason: {dump} or {self.configuration['autoDump']}"])

        return success


    def serialReadLine(self, dump : bool = False):
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

        if dump or self.configuration['autoDump']:
            Supporter.debugPrint([f"::serialReadLine:: serial dump [{Supporter.hexCharDump(retVal)}]", f"read/matched data [{retVal}]"])

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
    
            if dump or self.configuration['autoDump']:
                Supporter.debugPrint(f"::flush:: serial dump [{Supporter.hexCharDump(self.receivedData, ' ')}]")
        except Exception as exception:
            self.logger.warning(self, f"Exception caught in flush method: {exception}")

        self.receivedData = b""


    def serialRead(self, length : int = 0, regex : bytes = None, timeout : float = None, dump : bool = False):
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

        if dump or self.configuration['autoDump']:
            Supporter.debugPrint([f"::serialRead:: serial pre dump [{Supporter.hexCharDump(self.receivedData)}]", f"length = [{length}]", f"regex = [{regex}]", f"timeout = [{timeout}]"])

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
                            break       # leave loop since data has been found
                        else:
                            # send all data
                            returnData = self.receivedData
                        #Supporter.debugPrint(f"serialRead read ({Supporter.getSecondsSince(startTime)}s) [{returnData}]")

                # if timeout is <= 0, no length and no regex has been given, leave loop after first read without debug log
                if timeout <= 0 and not length and regex is None:
                    break       # leave loop because of single read
                elif Supporter.getSecondsSince(startTime) > timeout:
                    # if timeout has been given check if time is over (this works also if timeout was 0 and self.configuration["timeout"] was also 0)
                    self.receivedData = b""
                    self.logger.debug(self, f"timeout {len(self.receivedData)} {timeout} {self.receivedData}")
                    break       # leave loop because of timeout
                time.sleep(0.1)
        except Exception as exception:
            self.logger.warning(self, f"Exception caught in serialRead method: {exception}, re-init serial")
            self.reInitSerial()

        if dump or self.configuration['autoDump']:
            Supporter.debugPrint([f"::serialRead:: serial post dump (after {Supporter.getSecondsSince(startTime):.3f}s) [{Supporter.hexCharDump(self.receivedData)}]", f"read/matched data [{returnData}]"])

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

