import time
import subprocess
import json
import threading
import re
from datetime import datetime


from Base.Supporter import Supporter
from Base.ThreadObject import ThreadObject
from Logger.Logger import Logger


# command line interface:
# -----------------------
#     get signal command line interface from here:
#         https://github.com/AsamK/signal-cli
#     binaries are also available there
#
# Install:
# --------
#     pip3 install signal-cli-rest-api
#     pip3 install --upgrade setuptools
#     uvicorn signal_cli_rest_api.main:app --host 0.0.0.0 --port 8000
#
# Register new number via CLI:
# ----------------------------
#     signal-cli -a +1111111111111 register
#     --> Captcha required for verification, use --captcha CAPTCHA
#         To get the token, go to https://signalcaptchas.org/registration/generate.html        <--- !!!
#         Check the developer tools (F12) console for a failed redirect to signalcaptcha://
#         Everything after signalcaptcha:// is the captcha token.
#     signal-cli -a +1111111111111 register --voice --captcha <very long captcha token>
#     signal-cli -a +1111111111111 verify 333333
#     signal-cli -a +1111111111111 updateProfile --name <projectName>
#
# Send a message (and optionally trust a known number):
# -----------------------------------------------------
#     signal-cli -a +1111111111111 trust -a +2222222222222
#     signal-cli -a +1111111111111 send -m "Hallo" +2222222222222
#     signal-cli -a +1111111111111 receive


class SignalMessenger(ThreadObject):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        # check and prepare mandatory parameters
        self.tagsIncluded(["executable", "phone", "emergency"])
        if not self.tagsIncluded(["aliveTime"], intIfy = True, optional = True):
            self.configuration["aliveTime"] = 0
        if not self.tagsIncluded(["disabled"], intIfy = True, optional = True):
            self.configuration["disabled"] = 0


    def readerMethod(self, readToReadFrom, bufferToWriteTo, semaphore):
        '''
        Thread method can block while reading from signal-cli without any watch dog problems since it's not monitored
        '''
        while True:
            answer = self.signalPipe.stdout.readline()
            answer = answer.decode().strip()

            # for performance reasons only take messages start with an @
            if re.search(r"@", answer):
                with semaphore:
                    self.signalMessengerReadBuffer.append(answer)
            time.sleep(.1)


    def threadInitMethod(self):
        self.logger.info(self, "starting " + self.configuration["executable"])

        # setup pipes to and from signal-cli, see https://github.com/AsamK/signal-cli/discussions/679
        self.signalPipe = subprocess.Popen([self.configuration["executable"], "-u", self.configuration["phone"], "jsonRpc"],
                                           stdout = subprocess.PIPE,
                                           stderr = subprocess.PIPE,
                                           stdin  = subprocess.PIPE,
                                           shell = True)
        self.logger.info(self, "started " + self.configuration["executable"])

        # set up some object variables
        self.signalMessengerReadBuffer = []             # to fill in all received messages
        self.readBufferSemaphore = threading.Lock()     # semaphore for signal messenger receive buffer
        self.setupTimeOver = False                      # after a view seconds this value will be set to True and never set back to False, this is used that our reader sub thread has time to come up
        self.commandMessages = []                       # to fill in all received commands in threadMethod filtered from all the received messages for post-processing
        self.messageCounter = 0                         # message counter will be increased with each sent message
        self.stopMessageHandling = False                # in emergency case message handling can be stopped by sending "@stop"

        # set up and start reader task
        self.readerThread = threading.Thread(target = self.readerMethod, args = (self.signalPipe.stdout, self.signalMessengerReadBuffer, self.readBufferSemaphore), daemon = True)
        self.readerThread.start()

        # @todo SignalMessenger sollte sich bei Logger anmelden mit Warnschwelle, alle Nachrichten mit hoeherer Prio sollten verschickt werden!!!

        ###### NO!!!! self.mqttSendWatchdogAliveMessage({"disable":True})          # @todo enable this line for debugging only!


    def prepareSingalMessage(self, recipient, message):
        '''
        Prepare message string to be sendable via signal-cli
        '''
        self.messageCounter += 1
        sendData = {"jsonrpc":"2.0","method":"send","params":{"recipient":[recipient],"message":message},"id":self.messageCounter}
        sendData = ((json.dumps(sendData)) + "\n").encode('utf-8')
        return sendData


    def sendMessage(self, message : str, recipient : str = None):
        '''
        Prepare message and send it to recipient
        if recipient is not emergency number send it
        '''
        def sendPreparedMessage(sendMessage : bytes):
            # send message
            self.signalPipe.stdin.write(sendMessage)
            self.signalPipe.stdin.flush()
            #@todo error handling einbauen, falls pipe nicht OK, was passiert, wenn die konfigurierten Nummern falsch sind!!!

            # log message
            self.logger.info(self, "SENT: " + str(sendMessage))
        
        # send message to recipient
        header = ""     # onyl used in case recipient is not emergency contact
        if recipient is not None and not recipient == self.configuration["emergency"]:
            # prepare message
            sendMessage = self.prepareSingalMessage(recipient, message)
            sendPreparedMessage(sendMessage)
            header = "to ["+ recipient +"]: "       # add a header for message to emergency contact to get some extra information

        # always send message to emergency contact even if recipient was sb. else
        sendMessage = self.prepareSingalMessage(self.configuration["emergency"], header + message)
        sendPreparedMessage(sendMessage)

        return self.messageCounter


    def threadMethod(self):
        # initially give the signal-cli five seconds to come up
        if self.configuration["disabled"]:
            pass
        elif not self.setupTimeOver:
            if Supporter.timer(self.name + "_initTimer", timeout = 5):
                self.setupTimeOver = True
                Supporter.timer(self.name + "_initTimer", remove = True)
                self.sendMessage(self.get_projectName() + " is up and running... [" + str(datetime.now()) + "]")
        else:
            # main part when setup has been finished
            if self.configuration["aliveTime"] > 0:
                if Supporter.timer(self.name + "_aliveTimer", timeout = self.configuration["aliveTime"]):
                    self.sendMessage(self.get_projectName() + " is still alive... [" + str(datetime.now()) + "]")

            # anything received?
            with self.readBufferSemaphore:
                # handle all received messages
                while len(self.signalMessengerReadBuffer):
                    message = self.signalMessengerReadBuffer.pop(0)     # ensure buffer is cleared even if message is not handled afterwards!
                    
                    # message handling enabled? (in emergency case message handling can be disabled!)
                    if not self.stopMessageHandling:
                        jsonMessage = json.loads(str(message))
                        
                        # contains source number and contains message?
                        if (sourceNumber := Supporter.dictContains(jsonMessage, "params", "envelope", "sourceNumber")) and (message := Supporter.dictContains(jsonMessage, "params", "envelope", "dataMessage", "message")):
                            self.logger.info(self, "valid command from [" + sourceNumber + "] : [" + message + "]")
                            
                            # send info to emergency number if request was from another trusted number
                            if not sourceNumber == self.configuration["emergency"]:
                                self.sendMessage("from [" + sourceNumber + "]: " + message)

                            # only support trusted senders
                            if sourceNumber in self.configuration["trusted"]:
                                # check if there was a command included and handle it
                                if matches := re.search(r"^@echo\s+(.*)", message, re.MULTILINE):
                                    self.sendMessage(message, recipient = sourceNumber)
                                elif matches := re.search(r"^@help$", message, re.MULTILINE):
                                    self.sendMessage("@help\n" +
                                                     "@cmd <cmd>\n" +
                                                     "@echo <echo message>\n" +
                                                     "@get <value>\n" +
                                                     "@stop\n" +
                                                     "@exception"
                                                     , recipient = sourceNumber)
                                elif matches := re.search(r"^@stop$", message, re.MULTILINE):
                                    self.sendMessage(message, recipient = sourceNumber)
                                    self.stopMessageHandling = True
                                elif matches := re.search(r"^@exception$", message, re.MULTILINE):
                                    self.sendMessage(message, recipient = sourceNumber)
                                    self.stopMessageHandling = True
                                    raise Exception("initiated via signal message by [" + sourceNumber + "]")
                                else:
                                    self.logger.info(self, "command not handled: [" + message + "]")
                            else:
                                self.logger.warning(self, "not allowed sender [" + sourceNumber + "] sent " + str(jsonMessage))
                        else:
                            self.logger.info(self, "ignored message: " + str(jsonMessage))


    #def threadBreak(self):
    #    pass


    def threadTearDownMethod(self):
        # try to send a last message out!
        self.sendMessage(self.get_projectName() + " going down... [" + str(datetime.now()) + "]")
        time.sleep(1)       # give message some time to be sent out

