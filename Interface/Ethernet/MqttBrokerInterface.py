import time
import paho.mqtt.client as mqtt

from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter


class MqttBrokerInterface(InterfaceBase):
    '''
    classdocs
    '''

    _MOSQUITTO_SUBSCRIBE_TIMER_NAME = "mosquittoSubscribe"


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["user", "password", "server", "port", "sendRetained"])

    def connectMqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.dontCareList = {}
        self.logger.info(self, f"{self.name}: Try to establish MQTT connection")
        self.client.username_pw_set(self.configuration["user"], self.configuration["password"])

        # for any reason the one or other mqtt.Client() has problems with hostname "localhost", in that case try to get the IP instead
        if self.configuration["server"] == "localhost":
            self.configuration["server"] = "127.0.0.1"          # use it hard coded since getting the IP with socket.gethostbyname(socket.gethostname()) gives "127.0.1.1" what should be OK but doesn't work!?
        self.client.connect(self.configuration["server"], self.configuration["port"], 60 )

        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        _MOSQUITTO_INITIAL_TIMEOUT = 2
        self.InitialConnected = True

        self.logger.info(self, f"MQTT connected with result code " + str(rc))

        if not self.counter(name = self._MOSQUITTO_SUBSCRIBE_TIMER_NAME, value = 2, autoReset = False):
            timeout = _MOSQUITTO_INITIAL_TIMEOUT
        else:
            timeout = 0.1

        # (re-)setup one-shot-timer with timeout of 2 seconds
        self.timer(name = self._MOSQUITTO_SUBSCRIBE_TIMER_NAME, reSetup = True, timeout = timeout)

    def on_message(self, client, userdata, msg):
        tempTopic = str(msg.topic)
        #print(Supporter.hexAsciiDump(msg.payload))
        #print(Supporter.hexAsciiDump(tempTopic))
        tempMsg = str(Supporter.decode(msg.payload))
        self.logger.debug(self, f"MQTT message received: {tempMsg} from {tempTopic}")
        # if topic and msg is in dontCareList we will ignore the msg
        # we have to check first if topic is in the list
        if tempTopic in self.dontCareList:
            if self.dontCareList[tempTopic] == tempMsg:
                del self.dontCareList[tempTopic]
            else:
                self.mqttPublish(tempTopic, tempMsg, globalPublish = True, enableEcho = False)
        else:
            self.mqttPublish(tempTopic, tempMsg, globalPublish = True, enableEcho = False)

    def threadInitMethod(self):
        # subscribe internally global to get all global msg
        self.mqttSubscribeTopic("#", globalSubscription = True)

        self.InitialConnected = False

        tries = 0
        while tries < self.MAX_INIT_TRIES:
            try:
                # Try to connect to MQTT server, there could be a exception if ethernet or server is not available
                self.connectMqtt()
                break
            except:
                time.sleep(2)
                self.logger.info(self, f'Mosquitto connection init. {tries + 1} of {self.MAX_INIT_TRIES} failed.')
            tries += 1
        if tries >= self.MAX_INIT_TRIES:
            self.logger.warning(self, "Could not establish initial MQTT connection")


    def threadMethod(self):
        if self.timerExists(self._MOSQUITTO_SUBSCRIBE_TIMER_NAME):
            if self.timer(self._MOSQUITTO_SUBSCRIBE_TIMER_NAME, oneShot = True):
                # (re-)subscribe to projectName/# 
                self.client.subscribe(f"{self.get_projectName()}/#")

        # if there was no on_connect so far and our mqttRxQueue is filled up at a level of 90% we will try to clear the loop at least even if messages get lost
        if self.mqttRxQueue.qsize() >= (self.QUEUE_SIZE * 0.9):
            self.InitialConnected = True
            self.logger.error(self, "MQTT RX queue quiet full. Eventually we will lost messages.")

        if self.InitialConnected:
            while not self.mqttRxQueue.empty():
                newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
    
                # If messageType == Publish we have to publish The Data to MQTT Broker
                if newMqttMessageDict["global"]:
                    self.logger.debug(self, " received global queue message :" + str(newMqttMessageDict))
                    try:
                        self.client.publish(newMqttMessageDict["topic"], newMqttMessageDict["content"], retain = self.configuration["sendRetained"])
                        # we remember the msg to ignore incomming own msg
                        self.dontCareList[newMqttMessageDict["topic"]] = newMqttMessageDict["content"]
                    except:
                        self.logger.error(self, "Could not send MQTT msg to broker: "  + str(newMqttMessageDict))
                elif newMqttMessageDict["topic"] == self.createInTopic(self.getObjectTopic()):
                    # check here msg for class Mosquitto
                    self.logger.debug(self, " received queue message :" + str(newMqttMessageDict))
        else:
            self._mqttRxQueueGetIgnoreOnce = True


    def threadBreak(self):
        time.sleep(0.1)


    #def threadTearDownMethod(self):
    #    pass

