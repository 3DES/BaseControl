from Interface.Ethernet.TcpInterface import TcpInterface
#import Interface.Ethernet.TcpInterface


import socket
import re


#class EasyMeterTcpInterface(Interface.Ethernet.TcpInterface.TcpInterface):
class EasyMeterTcpInterface(TcpInterface):
    '''
    classdocs
    '''


    @classmethod
    def processBuffer(cls, buffer : str) -> list:
        '''
        process a received message and print it in formated way to STDOUT
        
        should be used for debugging and to analyze the protocoll since only searching the correct values usually is much faster
        '''
        def recursiveListHandler(buffer : str, index : int, data : list, entries : int, recursion : int) -> int:
            INDENT = 8
            while entries:
                entries -= 1        # one entry handled
                elementType = buffer[index]
                length = elementType & 0x0F
                subIndex = 1
    
                if elementType == 0x00:
                    # ignore fill byte
                    index += subIndex
                    print((" " * (INDENT * recursion)) + "00")
                    continue
    
                # extra length?            
                if elementType & 0x80:
                    length = (length << 4) | (buffer[index + subIndex] & 0x0F)
                    subIndex += 1
                
                if elementType & 0x70 == 0x70:
                    newList = []
                    data.append(newList)
                    print((" " * (INDENT * recursion)) + " ".join([ "{:02X}".format(char) for char in buffer[index:index + subIndex]]))
                    index = recursiveListHandler(buffer, index + subIndex, newList, length, recursion + 1)
                else:
                    data.append(buffer[index:index + length])
                    print((" " * (INDENT * recursion)) + " ".join([ "{:02X}".format(char) for char in buffer[index:index + length]]))
                    index += length
            return index
    
        #crc(buffer)
        
        index = 0
        print(" ".join([ "{:02X}".format(char) for char in buffer[:4]]))
        print(" ".join([ "{:02X}".format(char) for char in buffer[4:8]]))
        head = buffer[:8]
        tail = buffer[-8:]
        buffer = buffer[8:-8]
        data = [ head[:4], head[4:] ]
    
        # handle all lists in the current message
        while index < (len(buffer)):
            subIndex = 0
            elementType = buffer[index]
            length = elementType & 0x0F
            subIndex += 1
    
            if elementType == 0x00:
                # ignore fill byte
                index += subIndex
                print("00")
                continue
    
            # only list entries are allowed at top level
            if (elementType & 0x70) != 0x70:
                raise Exception(f"unknown element {buffer[index]} at {index}")
    
            # extra length?
            if elementType & 0x80:
                length = (length << 4) | (buffer[index + subIndex] & 0x0F)
                # second byte handled
                subIndex += 1
            
            newList = []
            data.append(newList)
    
            # handle rest of the current message recursively, if list ends maybe there is another one and we will come back to here with a new list entry
            print(" ".join([ "{:02X}".format(char) for char in buffer[index:index + subIndex]]))
            index = recursiveListHandler(buffer, index + subIndex, newList, length, 1)
    
    
        print(" ".join([ "{:02X}".format(char) for char in tail[:4]]))
        print(" ".join([ "{:02X}".format(char) for char in tail[4:]]))
        data.append(tail[:4])
        data.append(tail[4:])


    #def threadInitMethod(self):
    #    pass


    def threadInitMethod(self):
        super().threadInitMethod()      # we need the preparation from parental threadInitMethod 
        
        self.received = b""     # collect all received message parts here

        # patterns to match messages and values (the ^.*? will ensure that partial messages received at the beginning will be thrown away)
        self.smlPattern = re.compile(b"^.*?(\x1b{4}\x01{4}.*?\x1b{4}.{4})", re.MULTILINE | re.DOTALL)
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), "", globalPublish = True)

    
    def readData(self):
        #self.processBuffer(bytesArray)
        data = self.readSocket()
        if len(data):
            self.received += data               # add received data to receive buffer

            # full message received?
            if match := self.smlPattern.search(self.received):
                bytesArray = bytearray(match.groups()[0])
                # log message
                #hexString = ":".join([ "{:02X}".format(char) for char in bytesArray])
                #self.logger.info(self, f"#{len(match.groups()[0])}: {hexString}")
    
                # remove message from receive buffer
                self.received = self.smlPattern.sub(b"", self.received)

                #return bytesArray

            if len(self.received) > self.configuration["messageLength"]:
                self.logger.warning(self, f"cleared buffer because of buffer overflow prevention, length was {len(self.received)}")
                self.received = ""
           
        return ""


    #def threadMethod(self):
    #    pass


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

