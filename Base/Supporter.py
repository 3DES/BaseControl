'''
'''
import time
from datetime import datetime
import pydoc
import json
import re
from os.path import exists
import Logger
import sys
import Base
from gc import get_referents
import os


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
                    if not exists(fileName):
                        message = "cannot import [" + fileName + "] since it doesn't exist"
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
    def hexDump(cls, string):
        '''
        Create hex dump from given string (supports unicode strings, too)
        '''
        hexString = ""
        for unicodeChar in string:
            chars = str(unicodeChar)
            for char in chars:
                hexString += ":{:02x}".format(ord(char))
        return hexString


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
            hexString += " {:02x}".format(byte)
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

