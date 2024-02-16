import time
import json
import re
from Base.Supporter import Supporter
import Base.Crc
import colorama

from Interface.Uart.BasicUartInterface import BasicUartInterface
from GridLoad.EasyMeter import EasyMeter

class EasyMeterUartInterface(BasicUartInterface):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        self.removeMqttRxQueue()        # mqttRxQueue not needed so remove it

        if not self.tagsIncluded(["pollingPeriod"], intIfy = True, optional = True):
            self.configuration["pollingPeriod"] = 10     # default value if not given, 10 seconds are more than enough

        self.READ_TIMEOUT = 5       # if there was no data from easy meter after 5 seconds read will be stopped and thread loop will be left, so there will be no message for that turn!


    def threadInitMethod(self):
        super().threadInitMethod()      # we need the preparation from parental threadInitMethod 

        self.received = b""     # collect all received message parts here
        self.data = b""

        # patterns to match messages and values (the ^.*? will ensure that partial messages received at the beginning will be thrown away)
        self.SML_PATTERN = EasyMeter.getSmlPattern()

        #self.mqttPublish(self.createOutTopic(self.getObjectTopic()), "", globalPublish = True)        # to clear retained message from mosquitto


    def readAndPublishData(self):
        # clear serial so we receive completely new stuff
        self.serialReset_input_buffer()
        self.received = b""
        
        published = False

        while not published:
#xxxxx timeout hier einbauen, wenn nach 20 Sekunden immer noch nichts empfangen wurde!!!
#xxxxxx aufräumen
#xxxxxx message lesen genau erklären!!!
            data = self.serialRead()
            self.received += data               # add received data to receive buffer

            # full message received?
            if match := self.SML_PATTERN.match(self.received):
                #Supporter.debugPrint(f"pre-match [{len(match.group(1))}]\n{match.group(1)}", color = f"{colorama.Fore.GREEN}")
                message = bytearray(match.group(2))
                #Supporter.debugPrint(f"match [{len(message)}]\n{message}", color = f"{colorama.Fore.GREEN}")
                remaining = bytearray(match.group(3))
                #Supporter.debugPrint(f"remaining [{len(remaining)}]:\n{remaining}", color = f"{colorama.Fore.GREEN}")

                # throw pre-match away, independent if the rest of the message is OK or not, but keep message because even in error case the match could contain a valid part of the next message
                self.received = match.group(2) + match.group(3)

                # is there any stuff after last message than the very last message is not complete, so try to read again!
                if len(remaining):
                    continue

                # if the CRC of the last message is damaged try to receive a new one
                if Base.Crc.Crc.crc16EasyMeter(message[:-2]) != Base.Crc.Crc.twoBytesToWord(message[-2:]):
                    beautified = Supporter.hexAsciiDump(message)
                    #Supporter.debugPrint(f"match contains invalid message", color = f"{colorama.Fore.RED}")
                    continue

                # publish detected message
                self.mqttPublish(self.createOutTopic(self.getObjectTopic()), message, globalPublish = False, enableEcho = False)
                published = True
                #beautified = Supporter.hexAsciiDump(message)
                #Supporter.debugPrint(f"published {message}", color = f"{colorama.Fore.GREEN}")
                # in case of communication problems show the formatted SML data
                #EasyMeter.processBuffer(message)

                break

            if published:
                break

        return published


    def threadBreak(self):
        time.sleep(self.configuration["pollingPeriod"])


#    def threadTearDownMethod(self):
#        pass


#    def threadSummulationSupport(self):
#        '''
#        Necessary since this thread supports SIMULATE flag
#        '''
#        pass


    def threadMethod(self):
        #Supporter.debugPrint(f"search data")
        # get real values from easy meter
        published = self.readAndPublishData()
        #if published:
        #    Supporter.debugPrint(f"published [{published}] messages")

