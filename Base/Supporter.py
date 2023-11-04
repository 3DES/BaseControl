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
                            raise Exception("recursive import of json file " + loadFileStack[-1] + " detected")
        
                        initFile = open(fileName)                               # open init file
                        fileContent = ""                                        # for json validation, that's the only chance to get proper line numbers in case of error
                        for line in initFile:                                   # read line by line and remove comments
                            line = line.rstrip('\r\n')                          # remove trailing CRs and NLs
                            line = re.sub(r'#[^"\']*$', r'', line)              # remove comments, comments havn't to contain any quotation marks or apostrophes 
                            line = re.sub(r'^\s*#.*$', r'', line)               # remove line comments
                            fileContent += line + "\n"
                        initFile.close()
    
                        # try to json-ize imported file to get error messages with correct line numbers                
                        try:
                            dictMerge(jsonDictionary, json.loads(fileContent))
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
            if char <= 32 or char >= 127:    # replace non-readable ASCII values by its hex equivalent
                hexCharString += '{:02X}'.format(char)
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
                                LIGHTBLACK_EX
                                LIGHTBLUE_EX
                                LIGHTCYAN_EX
                                LIGHTGREEN_EX
                                LIGHTMAGENTA_EX
                                LIGHTRED_EX
                                LIGHTWHITE_EX
                                LIGHTYELLOW_EX
                                MAGENTA
                                RED
                                RESET
                                WHITE
                                YELLOW
        @param borderSize   amount of leading and trailing border lines to be printed
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
        colors = dict(colorama.Fore.__dict__.items())        
        if color in colors.keys():
            color = colors[color]

        # try to get object name but if not possible get class name instead
        if not (callerName := cls.getCallerName()):
            callerName = cls.getCaller().__class__.__name__ + "(class)"
        else:
            callerName += "(module)"

        printText = color
        for _ in range(borderSize):
            printText += f"    {marker * printLength}\n"
        printText += f"    # printed at {cls.getCallerPosition()}\n"
        if type(messageStringOrList) == str:
            messageStringOrList = [messageStringOrList]
        
        for index, string in enumerate(messageStringOrList):
            if index == 0:
                printText += f"    [{callerName}]: {string}\n"
            else:
                printText += f"    {string}\n"
                
        for _ in range(borderSize):
            printText += f"    {marker * (printLength - 5)}"
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
        
        @result    object of getCaller() callers caller or None if that doesn't exist
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
        
        @result    self.name of getCaller() callers caller or "" if that one has no self.name value
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
        
        @result    file name and line number of getCaller() callers caller
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
        @param force            if force is True the elementValue will be set the compare will return True
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

