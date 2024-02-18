'''
'''
import time
from datetime import datetime
import pydoc
import json
import re
import os.path
import Logger
import sys
import Base
from gc import get_referents
import os
import colorama
import inspect
from Base.ExtendedJsonParser import ExtendedJsonParser


class Supporter(object):
    '''
    classdocs
    '''
    @classmethod
    def loadInitFile(cls, initFileName : str, missingImportMeansError : bool):
        '''
        reads a json file and since json doesn't support any comments all detected comments will be removed,
        a comment is either a line containing blanks followed by a # sign and any further characters
        or a line conaining any stuff followed by a # sign and any further characters except quotation marks 
        , i.e.
            # comment 'line'                   -->   ""
            "a" : "b",    # trailing comment   -->   "a" : "b",
            "x" : "y",    # not a 'comment'    -->   "x" : "y",    # not a 'comment'
        '''
        def dictMerge(targetDict : dict, sourceDict : dict):
            '''
            Merges two dicts by adding elements from one into the other.
            If elements in source and in target dict are also dicts it will recursively merge them.
            If one or both elements aren't dicts the element in the target dict will be replaced by the one in the source dict, this means that e.g. lists will be replaced and list elements from target list will get lost.
            '''
            for sourceElement in sourceDict:
                if sourceElement in targetDict and (type(targetDict[sourceElement]) is dict) and (type(sourceDict[sourceElement]) is dict):
                    dictMerge(targetDict[sourceElement], sourceDict[sourceElement])
                else:
                    targetDict[sourceElement] = sourceDict[sourceElement]


        extendedJsonParser = ExtendedJsonParser()      # get a extended json parser        
        loadFileStack = []      # needed to prevent recursive import of json files
        def loadPseudoJsonFile(jsonDictionary : dict):
            if "@import" in jsonDictionary:
                fileNameList = jsonDictionary["@import"]

                if isinstance(fileNameList, str):
                    fileNameList = [fileNameList]

                del(jsonDictionary["@import"])

                for fileName in fileNameList:
                    if not os.path.exists(fileName):
                        message = "cannot import [" + fileName + "] since it doesn't exist"
                        files = os.listdir()
                        for file in files:
                            print(file)
                        files = os.listdir("json")
                        for file in files:
                            print(file)
                        if missingImportMeansError:
                            raise Exception(message)
                        else:
                            Logger.Logger.Logger.error(cls, message)
                    else:
                        # add file to loadFileStack for recursive import detection
                        loadFileStack.append(fileName)
                        if len(loadFileStack) != len(set(loadFileStack)):
                            # the last added file name was already on the stack, that means a recursion has been detected!
                            raise Exception("recursive import of json file " + loadFileStack[-1] + " detected")

                        # try to json-ize imported file to get error messages with correct line numbers                
                        try:
                            dictMerge(jsonDictionary, extendedJsonParser.parseFile(fileName))
                        except Exception as exception:
                            raise Exception("error in json file " + fileName + " -> " + str(exception))

                        jsonDictionary = loadPseudoJsonFile(jsonDictionary)

                        # remove current file from loadFileStack
                        loadFileStack.pop()
            return jsonDictionary

        # return completely loaded init file
        return loadPseudoJsonFile({ "@import" : initFileName })        # initial content to import given "init.json" file


    @classmethod
    def encloseString(cls, string, leftEnclosing : str = "[", rightEnclosing : str = "]"):
        '''
        formats given string by enclosing it in given left and right enclosing string, e.g.
            FOOBAR -->  [FOOBAR]
        '''
        return leftEnclosing + str(string) + rightEnclosing


    @classmethod
    def getTimeStamp(cls):
        return time.time()


    @classmethod
    def getDeltaTime(cls, startTime : float, endTime : float = None):
        if endTime is None:
            endTime = cls.getTimeStamp()
        return endTime - startTime


    @classmethod
    def getSecondsSince(cls, timeStamp : int):
        return cls.getTimeStamp() - timeStamp


    @classmethod
    def getTimeOfToday(cls, year : int = None, month : int = None, day : int = None, hour : int = 0, minute : int = 0, second : int = 0):
        '''
        Time of today 0 o'clock if no value has been given otherwise the time of today at given time
        '''
        nowTime = datetime.now()
        if year  is not None: nowTime.replace(year = year)
        if month is not None: nowTime.replace(month = month)
        if day   is not None: nowTime.replace(day = day)
        return int(nowTime.replace(hour=hour,minute=minute,second=second,microsecond=0).timestamp())


    @classmethod
    def loadClassFromFile(cls, fullClassName : str):
        '''
        loads a class from a given file
        no object will be created only the class will be loaded and given back to the caller

        :param   fullClassName: name of the class including package and module to be loaded (e.g. Logger.Logger.Logger means Logger class contained in Logger.py contained in Logger folder)
        :return: loaded but not yet instantiated class
        :rtype:  module
        :raises  Exception: if given module doesn't exist
        '''
        className = fullClassName.rsplit('.')[-1]
        classType = ".".join(fullClassName.rsplit('.')[0:-1])
        loadableModule = pydoc.locate(classType)

        if loadableModule is None:
            raise Exception("there is no module \"" + classType + "\"")

        Logger.Logger.Logger.trace(cls, "loading: module = " + str(loadableModule) + ", className = " + str(className) + ", classType = " + str(classType))
        loadableClass = getattr(loadableModule, className)
        return loadableClass


    @classmethod
    def dictContains(cls, testDict : dict, *args):
        for argument in args:
            if argument not in testDict:
                return None
            else:
                testDict = testDict[argument]
        return testDict
        

    # @todo
    ###@classmethod
    ###def memCheck(self):
    ####    def getsize(obj):
    ####        """sum size of object & members."""
    ####        BLACKLIST = type
    ####        if isinstance(obj, BLACKLIST):
    ####            raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    ####        seen_ids = set()
    ####        size = 0
    ####        objects = [obj]
    ####        while objects:
    ####            need_referents = []
    ####            for obj in objects:
    ####                if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
    ####                    seen_ids.add(id(obj))
    ####                    size += sys.getsizeof(obj)
    ####                    need_referents.append(obj)
    ####            objects = get_referents(*need_referents)
    ####        return size
    ####
    ####        
    ####    print(getsize(Base.ThreadBase.ThreadBase.get_setupThreadObjects()))
    ###    print("----------------------------------")
    ###    print(psutil.cpu_percent())
    ###    print(psutil.virtual_memory())  # physical memory usage
    ###    print('memory % used:', psutil.virtual_memory()[2])
    ###    pid = os.getpid()
    ###    print("PID: " + str(pid))
    ###    python_process = psutil.Process(pid)
    ###    memoryUse = python_process.memory_info()[0]/2.**30  # memory use in GB...I think
    ###    print('memory use:', memoryUse)        
    ###    print("----------------------------------")
    ###    pass


        
        
        #for name, size in sorted(((name, sys.getsizeof(value)) for name, value in globals().items()),
        #                         key= lambda x: -x[1])[:10]:
        #    print("{:>30}: {:>8}".format(name, sizeof_fmt(size)))


    @classmethod
    def hexDump(cls, string, separator : str = ''):
        '''
        Create hex dump from given string (supports unicode strings, too)
        '''
        hexString = ""
        for unicodeChar in string:
            chars = str(unicodeChar)
            for char in chars:
                hexString += ":{:02X}".format(ord(char))
                if separator:
                    hexString += separator
        if separator:
            hexString = hexString[:-len(separator)]
        return hexString


    @classmethod
    def hexCharDump(cls, string, separator : str = ''):
        '''
        Create hex/char dump from given string
        '''
        hexCharString = ""
        for index, char in enumerate(string):
            if type(char) == str:
                char = ord(char)
            if char < 32 or char >= 127:    # replace non-readable ASCII values by its hex equivalent
                hexCharString += '\\x{:02X}'.format(char)
            else:
                hexCharString += chr(char)
            if separator and index < (len(string) - 1):
                hexCharString += separator
        return hexCharString


    @classmethod
    def hexAsciiDump(cls, string, width : int = 16):
        hexString = ""
        asciiString = ""
        overallString = ""
        charCounter = 0

        def byteDump(byte):
            nonlocal hexString
            nonlocal asciiString
            nonlocal overallString
            nonlocal charCounter
            hexString += " {:02X}".format(byte)
            asciiString += chr(byte) if (byte > 32 and byte < 127) else "."
            charCounter += 1
            if charCounter % width == 0:
                overallString += f"{hexString}    {asciiString}\n"
                asciiString = ""
                hexString   = ""
            #if charCounter % width == width / 2:
            #    asciiString += " "

        # select correct dump method and call it
        if isinstance(string, str):
            charCounter = 0
            for unicodeChar in string:
                chars = str(unicodeChar)
                for char in chars:
                    byteDump(ord(char))
        else:
            for byte in string:
                byteDump(byte)

        # enlarge last line if necessary but not if it's the only line
        if len(hexString) and (charCounter > width):
            if len(asciiString) < width:
                hexString   += "   " * (width - len(asciiString))
            overallString += f"{hexString}    {asciiString}\n"
        return overallString


    @classmethod
    def hexStrToAscii(cls, data):
        '''
        Converts given hex string to ASCII, e.g. "414243" will become "ABC"
        '''
        if type(data) not in [bytearray, bytes, str]:
            raise Exception(f"given data is of unsupported type {type(data)}")

        if type(data) == bytearray or type(data) == bytes:
            data = data.decode('utf-8')
        return bytearray.fromhex(data).decode('utf-8')


    @classmethod
    def asciiToHexStr(cls, data):
        '''
        Converts given ASCII to hex string, e.g. "ABC" will become "414243"
        '''
        if type(data) not in [bytearray, bytes, str]:
            raise Exception(f"given data is of unsupported type {type(data)}")

        if type(data) == bytearray or type(data) == bytes:
            data = data.decode('utf-8')
        return bytearray.fromhex(data).decode('utf-8')


    @classmethod
    def bytesToStr(cls, data : bytes) -> str:
        '''
        Converts given bytes string to normal string, i.e. b"abc" -> "abc"
        '''
        return data.decode('utf-8')


    @classmethod
    def changeByteOrderOfHexString(cls, hexString : bytes, ignoredCharacters = None, stopCharacters = None) -> bytes:
        '''
        Converts byte hex string to byte-swapped hex string, i.e. b"ABCDEF" -> b"EFCDAB"
        '''
        if len(hexString) % 2:
            raise Exception(f"given hex string [{hexString}] must have an even length but {len(hexString)} is odd")
        newHexString = b""
        for byte in re.findall(b"..", hexString):
            # stop characters found?
            if stopCharacters and byte in stopCharacters:
                break
            # characters to be handled found?
            if not ignoredCharacters or byte not in ignoredCharacters:
                newHexString = byte + newHexString
        return newHexString


    @classmethod
    def countSetBits(cls, value : int) -> int:
        '''
        Counts bits that are 1 in given value
        
        @param value    the value where the one-bits should be counted
        @resut          amount of one-bits found
        '''
        bitsNotZero = 0
        while value:
            if value & 0x01:
                bitsNotZero += 1
            value >>= 1
        return bitsNotZero


    @classmethod
    def shiftToLeastNotZeroBit(cls, value : int) -> int:
        '''
        Shifts the given value until the least significant bit becomes one, e.g. 0x030 -> 0x003, 0x102 -> 0x81, 0x01 -> 0x01, ...
        
        @param value    the value that has to be right shifted
        @resut          right shifted value
        '''
        while value and not (value & 0x01):
            value >>= 1
        return value


    @classmethod
    def leastNotZeroBit(cls, value : int) -> int:
        '''
        Searches the least significant one-bit in the given value, e.g. 0x030 -> 4, 0x01 -> 0, 0x00 -> None, ...
        
        @param value    the value where the least significant one-bit has to be searched
        @resut          position of the least significant one-bit
        '''
        position = None
        if value:
            position = 0
            while not (value & 0x01):
                value >>= 1
                position += 1
        return position


    @classmethod
    def decode(cls, string):
        return string.decode('ISO-8859-1')


    @classmethod
    def encode(cls, string):
        return string.encode('ISO-8859-1')


    @classmethod
    def absoluteDifference(cls, value1 : int, value2 : int):
        '''
        Absolute difference between two given values
        '''
        difference = value1 - value2;
        if difference < 0:
            difference = -difference
        return difference


    @classmethod
    def deltaOutsideRange(cls, newValue : float, oldValue : float, minValue : float = None, maxValue : float = None, percent : float = 0.0, dynamic : bool = False, minIgnoreDelta : float = 0.0):
        '''
        Can be used to decide if a delta between two values has an certain amount.

        @param newValue            new value that has to be checked
        @param oldValue            last accepted value
        @param minValue            the new value has to be larger than or equal to min value
        @param maxValue            the new value has to be smaller than or equal to max value
        @param percent             percent range, the new value must be outside of the range [old value - percent, old value + percent]
        @param dynamic             if False [minValue, maxValue] will be used as range so ignore range has always same size, if True the smaller the value is the smaller the ignore range will be, if minValue and/or maxValue is None then dynamic is True
        @param minIgnoreDelta      the difference between the old and the new value has to be at least "old value * percent"

        @return    True if new value is inside [minValue, maxValue] range on the one side but outside of the ignore range [oldValue - ignoreDelta, oldValue + ignoreDelta]
        '''
        if dynamic or minValue is None or maxValue is None:
            valueRange = min(oldValue, newValue)            # ignore delta will be smaller if current value is smaller
        else:
            valueRange = abs(maxValue - minValue)           # ignore delta only depends on valid value range but not on current value

        ignoreDelta = valueRange * (percent / 100)
        ignoreDelta = max(ignoreDelta, minIgnoreDelta)      # ensure a minimum ignore delta size if one has been given

        delta = abs(oldValue - newValue)                    # calculate difference between old an new value to decide if change is inside or outside of the ignore window

        compareResult = (delta >= ignoreDelta)
        
        if minValue is not None and maxValue is not None:
            compareResult &= (minValue <= newValue <= maxValue)

        # if given value is valid check if its difference to the old value is greater or equal to +/- ignore delta
        return compareResult


    @classmethod
    def convertColor(cls, color : str) -> str:
        '''
        @param color        color should be either one of the supported colors, e.g. RED, GREEN, YELLOW or BLUE or a colorama.Fore.<color> string
                            The following keys are known by colorama.Fore and can be used:
                                BLACK
                                BLUE
                                CYAN
                                GREEN
                                MAGENTA
                                RED
                                RESET
                                WHITE
                                YELLOW
                                LIGHTBLACK   / LIGHTBLACK_EX
                                LIGHTBLUE    / LIGHTBLUE_EX
                                LIGHTCYAN    / LIGHTCYAN_EX
                                LIGHTGREEN   / LIGHTGREEN_EX
                                LIGHTMAGENTA / LIGHTMAGENTA_EX
                                LIGHTRED     / LIGHTRED_EX
                                LIGHTWHITE   / LIGHTWHITE_EX
                                LIGHTYELLOW  / LIGHTYELLOW_EX
        '''
        colors = dict(colorama.Fore.__dict__.items())
        if color in ["LIGHTBLACK", "LIGHTBLUE", "LIGHTCYAN", "LIGHTGREEN", "LIGHTMAGENTA", "LIGHTRED", "LIGHTWHITE", "LIGHTYELLOW"]:
            color += "_EX"
        if color in colors.keys():
            color = colors[color]
        return color


    @classmethod
    def printTimeStamp(cls, message : str = None, startTime : float = None, color : str = None):
        '''
        Prints time stamp to STDOUT with an optional message and an optional delta time

        So it can be used for timing measurement, e.g.
            startTime = Supporter.printTimeStamp(message = "position xy")
            for ...:
                ... 
                startTime = Supporter.printTimeStamp(message = "position xy", startTime = startTime)

        @param message      optional message to be printed together with time stamp
        @param startTime    if start time has been given a delta time will be calculated and printed
        @param color        default color is YELLOW but any other color can be given here
        @return             current time stamp
        '''
        timeStamp = cls.getTimeStamp()

        DEFAULT_COLOR = "YELLOW"
        if color is None:
            color = DEFAULT_COLOR
        color = cls.convertColor(color.upper())
        
        printText = color
        printText += f"time: {timeStamp}"
        if startTime is not None:
            printText += f", delta: {timeStamp - startTime}"
        if message:
            printText += f", message:\"{message}\""
        printText += f" at [{cls.getCallerPosition()}]"
        print(printText, flush=True)
        return timeStamp


    @classmethod
    def debugPrint(cls, messageStringOrList, marker : str = None, color : str = None, borderSize : int = 1):
        '''
        Print given stuff in eye-catching manner
        message will be printed between a frame, the frame has borderSize leading and trailing lines
        the frame is printed witch given character "marker" or with "#" as default character, but marker can be longer than a character if necessary
        an optional color code, e.g. "colorama.Fore.YELLOW" can be given
        
        @param message      message to be printed, caller's name will be added in front of it in square brackets
        @param marker       character (or string) that will be used to print the border
        @param color        default color is yellow but another color can be given, either one of the supported colors, e.g. RED, GREEN, YELLOW or BLUE or a colorama.Fore.<color> string
                            The following keys are known by colorama.Fore and can be used:
                                BLACK
                                BLUE
                                CYAN
                                GREEN
                                MAGENTA
                                RED
                                RESET
                                WHITE
                                YELLOW
                                LIGHTBLACK   / LIGHTBLACK_EX
                                LIGHTBLUE    / LIGHTBLUE_EX
                                LIGHTCYAN    / LIGHTCYAN_EX
                                LIGHTGREEN   / LIGHTGREEN_EX
                                LIGHTMAGENTA / LIGHTMAGENTA_EX
                                LIGHTRED     / LIGHTRED_EX
                                LIGHTWHITE   / LIGHTWHITE_EX
                                LIGHTYELLOW  / LIGHTYELLOW_EX
        @param borderSize   amount of leading and trailing border lines to be printed, if it's set to 0 only a single line with the message will be printed
        '''
        MAX_LENGTH = 60
        DEFAULT_COLOR = "YELLOW"
        DEFAULT_BORDER = "#"

        if marker is not None and len(marker):
            printLength = int((MAX_LENGTH + (len(marker) - 1)) / len(marker))
        else:
            printLength = MAX_LENGTH
            marker = DEFAULT_BORDER

        if color is None:
            color = DEFAULT_COLOR
        color = cls.convertColor(color.upper())

        # try to get object name but if not possible get class name instead
        if not (callerName := cls.getCallerName()):
            callerName = cls.getCaller().__class__.__name__ + "(class)"
        else:
            callerName += "(module)"

        if type(messageStringOrList) == str:
            messageStringOrList = [messageStringOrList]

        printText = color

        if borderSize:
            for _ in range(borderSize):
                printText += f"    {marker * printLength}\n"
            printText += f"    # printed at {cls.getCallerPosition()}\n"
            
            printText += f"    # {datetime.now()} [{callerName}]\n"
            
            for index, string in enumerate(messageStringOrList):
                printText += f"    # {string}\n"
                    
            for _ in range(borderSize):
                printText += f"    {marker * (printLength - 5)}\n"
        else:
            printText += "    " + (marker * 4) + " "
            printText += f"{datetime.now()} [{callerName}] \"" + " ".join(messageStringOrList) + "\" "
            printText += f"# at {cls.getCallerPosition()}"
        printText += f"{colorama.Style.RESET_ALL}"
        print(printText, flush=True)


    @classmethod
    def formattedUptime(cls, timeInSeconds : int, noSeconds : bool = False):
        timeInSeconds = int(timeInSeconds)          # yes, this is necessary, otherwise the values are e.g. "02.0" and not "02"; don't know why since parameter is also defined as int!?!?
        days    = timeInSeconds // (24 * 60 * 60)
        timeInSeconds %=           (24 * 60 * 60)
        hours   = timeInSeconds // (60 * 60)
        timeInSeconds %=           (60 * 60)
        minutes = timeInSeconds // 60
        timeInSeconds %=           60
        seconds = timeInSeconds

        timeString = f"{days}d {hours:02}:{minutes:02}"

        if not noSeconds:
            timeString += f":{seconds:02}"

        return timeString


    @classmethod
    def formattedTime(cls, timeInSeconds : int, addCurrentTime : bool = False, noSeconds : bool = False, shortTime : bool = False):
        def pluralify(string : str, value : int):
            if value != 1:
                return string + 's'
            else:
                return string

        timeInSeconds = int(timeInSeconds)          # yes, this is necessary, otherwise the values are e.g. "02.0" and not "02"; don't know why since parameter is also defined as int!?!?
        timeString = ""

        if addCurrentTime:
            timeString += datetime.now().strftime("%d/%m/%Y - %H:%M:%S - ")      # noSeconds only influence given value timeInSeconds but not the current time part

        if shortTime:
            timeString += datetime.fromtimestamp(timeInSeconds).strftime("%d/%m/%Y - %H:%M:%S")
        else:
            days    = timeInSeconds // (24 * 60 * 60)
            timeInSeconds %=           (24 * 60 * 60)
            hours   = timeInSeconds // (60 * 60)
            timeInSeconds %=           (60 * 60)
            minutes = timeInSeconds // 60
            timeInSeconds %=           60
            seconds = timeInSeconds
    
    
            if days:
                timeString += f"{days} {pluralify('day', days)}, "
    
            if days or hours: 
                timeString += f"{hours:02} {pluralify('hour', hours)}, "
            
            timeString     += f"{minutes:02} {pluralify('min', minutes)}"
            
            if not noSeconds:
                timeString += f", {seconds:02} {pluralify('second', seconds)}"

        return timeString


    @classmethod
    def getCallStack(cls, skip : int = 2):
        '''
        Create call stack string and give it back
        '''
        callStackString = ""
        callStack = inspect.stack()
        indent = len(callStack) - 1 - skip

        for index, stackIndex in enumerate(range(skip, len(callStack) - 1)):
            callStackString += "  " * indent
            parentframe = callStack[stackIndex]
            fileName   = parentframe.filename
            lineNumber = parentframe.lineno
            if 'self' in parentframe[0].f_locals:
                moduleClass = parentframe[0].f_locals['self'].__class__.__name__
                if hasattr(parentframe[0].f_locals['self'], 'name'):
                    moduleName  = parentframe[0].f_locals['self'].name
                    callStackString += f"{index}: {moduleClass}({moduleName}) - {parentframe[0].f_locals['self'].name} - {fileName}:{lineNumber}"
                else:
                    callStackString += f"{index}: {moduleClass} - {fileName}:{lineNumber}"
            else:
                callStackString += f"{index}: {fileName}:{lineNumber}"

            # re-calculate indent, and add a new line as long as there are further calls
            indent -= 1
            if indent:
                callStackString += "\n"

        return callStackString


    @classmethod
    def getCaller(cls, skip : int = 2, getSelf : bool = True) -> object:
        '''
        Returns object of the caller that called the method that called getCaller()
        
        @param skip       default is 2 since caller of getCaller() would be one but caller of getCaller() wants to know its caller so there are two
        @param getSelf    returns object.self if True, otherwise the whole frame is returned
        
        @return    object of getCaller() callers caller or None if that doesn't exist
        '''
        callStack = inspect.stack()
        stackIndex = skip
        parentframe = callStack[stackIndex]
        if getSelf and ('self' in parentframe[0].f_locals):
            return parentframe[0].f_locals['self']
        else:
            return parentframe


    @classmethod
    def getCallerName(cls, skip : int = 2) -> str:
        '''
        Returns self.name of the caller that called the method that called getCaller()
        
        @param skip    default is 2 since caller of getCaller() would be one but caller of getCaller() wants to know its caller so there are two
        
        @return    self.name of getCaller() callers caller or "" if that one has no self.name value
        '''
        caller = cls.getCaller(skip = skip + 1)        # skip one more since this method getCallerName() has also be skipped
        if hasattr(caller, 'name'):
            return caller.name
        return ""


    @classmethod
    def getCallerPosition(cls, skip : int = 2) -> str:
        '''
        Returns file name and line number of the caller that called the method that called getCaller()
        
        @param skip    default is 2 since caller of getCaller() would be one but caller of getCaller() wants to know its caller so there are two
        
        @return    file name and line number of getCaller() callers caller
        '''
        caller = cls.getCaller(skip = skip + 1, getSelf = False)        # skip one more since this method getCallerName() has also be skipped
        return f"{caller.filename}:{caller.lineno}"


    @classmethod
    def compareAndSetDictElement(cls, dictionary : dict, elementName, elementValue, compareValue : bool = False, compareMethod : callable = None, force : bool = False) -> bool:
        '''
        Checks if a given element is contained in a given dictionary and if so it compares the two values
        If the element is not contained or the elements are not equal, the element will be inserted/changed and True will be given back
        
        @param dictionary       dictionary that should be checked
        @param elementName      name of the element in the dictionary that should be checked
        @param elementValue     value the element in the dictionary should be compared to
        @param compareValue     for easier check if sth. has changed a boolean can be given that will be "OR"-ed with previous checks simply
                                by giving back True if sth. has been changed or the given boolean in case nth. has been changed
        @param force            if force is True the elementValue will be set and the compare will return True
        @return        False/compareValue in case nth. has been changed, True in case sth. has been changed or force was True
        '''
        toBeSet = force
        if elementName in dictionary:
            if (compareMethod is not None):
                toBeSet |= compareMethod(elementValue, dictionary[elementName])
            else:
                toBeSet |= (dictionary[elementName] != elementValue)
        else:
            toBeSet = True

        if toBeSet:
            dictionary[elementName] = elementValue
            return True

        return compareValue

