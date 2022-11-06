import time
import subprocess
import json
import threading
import re
from datetime import datetime
from queue import Queue
import sys
import gc


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
        self.tagsIncluded(["executable", "emergency"])
        self.tagsIncluded(["restartLimit", "restartTime"], intIfy = True)
        if not self.tagsIncluded(["aliveTime"], intIfy = True, optional = True):
            self.configuration["aliveTime"] = 0
        if not self.tagsIncluded(["disabled"], intIfy = True, optional = True):
            self.configuration["disabled"] = 0
        if not isinstance(self.configuration["executable"], list):
            raise Exception(self.name() + " needs a \"executable\" value in init file that is a list")


    def readSignalMessengerThread(self, pipe : subprocess.PIPE, partner : subprocess.Popen, queue : Queue = None, stdErrReader : bool = False):
        '''
        Thread method can block while reading from signal-cli without any watch dog problems since it's not monitored
        '''
        while True:
            if partner.poll() is None:
                pipe.flush()
                message = pipe.readline()               # blocking read
                print("msg: " + str(message) + "\nhex:" + Supporter.hexDump(str(message)) + "\nlen:" + str(len(message)) + "\n")

                # ignore empty lines
                if not len(message):
                    continue

                message = message.decode().strip()
                # reading on STDERR or on STDOUT?
                if stdErrReader:
                    self.logger.warning(self, "signal-cli stderr: " + message)
                else:
                    self.logger.info(self, "signal-cli stdout: " + message)
                    queue.put(message)
                
                time.sleep(.1)          # be nice
            else:
                self.logger.error(self, "signal-cli died " + ("(stderr)" if stdErrReader else "(stdout)"))
                return


    def setupReaders(self):
        '''
        Try to startup signal messenger interface
        '''
        self.logger.info(self, "signal-cli start handler started")

        if not hasattr(self, "signalReadQueue"):
            self.signalReadErrQueue = Queue()               # data from signal messenger's STDERR
            self.signalReadQueue = Queue()                  # data from signal messenger's STDOUT
        self.setupTimeOver = False                      # after a view seconds this value will be set to True and never set back to False, this is used that our reader sub thread has time to come up

        # setup pipes to and from signal-cli, see https://github.com/AsamK/signal-cli/discussions/679
        self.signalPipe = subprocess.Popen(self.configuration["executable"],
                                           stdout = subprocess.PIPE,
                                           stderr = subprocess.PIPE,
                                           stdin  = subprocess.PIPE,
                                           shell = True,
                                           close_fds = 'posix' in sys.builtin_module_names)

        # set up and start reader task
        self.readStdErrThread = threading.Thread(target = self.readSignalMessengerThread, args = (
            self.signalPipe.stderr,
            self.signalPipe,
            None,
            True), daemon = True)
        self.readStdErrThread.start()
        
        self.readStdOutThread = threading.Thread(target = self.readSignalMessengerThread, args = (
            self.signalPipe.stdout,
            self.signalPipe,
            self.signalReadQueue,
            False), daemon = True)
        self.readStdOutThread.start()

        self.logger.info(self, "signal-cli start handler finished")

        return True


    def threadInitMethod(self):
        self.logger.info(self, "starting " + " ".join(self.configuration["executable"]))

        # set up some object variables
        self.messageCounter = 0                         # message counter will be increased with each sent message
        self.stopMessageHandling = False                # in emergency case message handling can be stopped by sending "@stop"

        self.setupReaders()

        self.logger.info(self, "started " + " ".join(self.configuration["executable"]))

        # @todo SignalMessenger sollte sich als Uebertrager bei Logger anmelden mit Warnschwelle, alle Nachrichten mit hoeherer Prio sollten per Signal verschickt werden!!!


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
            try:
                # try to send message
                self.signalPipe.stdin.write(sendMessage)
                self.signalPipe.stdin.flush()
                self.logger.info(self, "sent: " + str(sendMessage))
            except Exception as exception:
                # in error case show info but let the SignalMessenger main loop handle it
                self.logger.error(self, "failed sending: " + str(sendMessage) + "\n" + str(exception))


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
            if not hasattr(self, "disableWarningSent"):
                self.disableWarningSent = True
                self.logger.warning(self, self.name + " is disabled via init file")
        elif not self.setupTimeOver:
            if Supporter.timer(self.name + "_initTimer", timeout = 5):
                self.setupTimeOver = True
                Supporter.timer(self.name + "_initTimer", remove = True)
        else:
            # main part when setup has been finished
            # anything received?
            while not self.mqttRxQueue.empty():
                newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
                self.logger.debug(self, "received message :" + str(newMqttMessageDict))
                # @todo do sth. with messages received from any thread here...

            # handle all received errors
            if (value := self.signalPipe.poll()) is not None:
                if not hasattr(self, "signalRestarted") or self.signalRestarted:
                    self.logger.error(self, "signal-cli died (thread)")
                    self.signalRestarted = False         # event logged, don't log it again until signal-cli hasn't been started again

                self.initialMessageSent = False         # startup message will be sent again!

                if self.setupReaders():
                    self.logger.info(self, "signal-cli re-started")
                    self.signalRestarted = True          # signal-cli started again, enable event logging again in case it dies again

                return  # leave loop again and let "not self.setupTimeOver" part run again

            # send initial message via signal
            if not hasattr(self, "initialMessageSent") or not self.initialMessageSent:
                self.initialMessageSent = True
                self.sendMessage(self.get_projectName() + " is up and running... [" + str(datetime.now()) + "]")

            # send alive message if configured and alive time is over
            if self.configuration["aliveTime"] > 0:
                if Supporter.timer(self.name + "_aliveTimer", timeout = self.configuration["aliveTime"]):
                    self.sendMessage(self.get_projectName() + " is still alive... [" + str(datetime.now()) + "]")


            # handle all received signal messages
            while not self.signalReadQueue.empty():
                message = self.signalReadQueue.get(block = False)

                # message handling enabled? (in emergency case message handling can be disabled!)
                if not self.stopMessageHandling:
                    jsonMessage = json.loads(str(message))
                    self.logger.info(self, "message received: " + str(jsonMessage))
                    
                    # contains source number and contains message?
                    if (sourceNumber := Supporter.dictContains(jsonMessage, "params", "envelope", "sourceNumber")) and (message := Supporter.dictContains(jsonMessage, "params", "envelope", "dataMessage", "message")):
                        self.logger.info(self, "valid message from [" + sourceNumber + "] : [" + message + "]")

                        # send info to emergency number if request was from another trusted number
                        if not sourceNumber == self.configuration["emergency"]:
                            self.sendMessage("from [" + sourceNumber + "]: " + message)

                        # only support trusted senders
                        if sourceNumber in self.configuration["trusted"]:

                            # for performance reasons only take messages start with @
                            if re.search(r"@", message):
                                self.logger.info(self, "command from [" + sourceNumber + "] : [" + message + "]")

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
                                    self.logger.info(self, "unknown command: [" + message + "]")
                                    self.sendMessage("unknown command, please try @help", recipient = sourceNumber)
                            else:
                                self.logger.warning(self, "not a command message")
                                self.sendMessage("unknown command, please try @help", recipient = sourceNumber)
                        else:
                            self.logger.warning(self, "not allowed sender [" + sourceNumber + "]")
                    else:
                        self.logger.info(self, "message ignored")


    #def threadBreak(self):
    #    pass


    def threadTearDownMethod(self):
        # try to send a last message out!
        self.sendMessage(self.get_projectName() + " shut down... [" + str(datetime.now()) + "]")
        time.sleep(1)       # give message some time to be sent out

