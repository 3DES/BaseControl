import time
import paho.mqtt.client as mqtt
import json

from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter
from MqttBridge.MqttBridge import MqttBridge


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
        self.tagsIncluded(["user", "password", "server"])
        self.tagsIncluded(["internalBridge"], optional = True, default = "MqttBridge")
        self.tagsIncluded(["port"], optional = True, default = 1883)
        self.tagsIncluded(["sendRetained"], optional = True, default = True)

    def connectMqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.logger.info(self, f"{self.name}: Try to establish MQTT connection")
        self.client.username_pw_set(self.configuration["user"], self.configuration["password"])

        # for any reason the one or other mqtt.Client() has problems with hostname "localhost", in that case try to get the IP instead
        if self.configuration["server"] == "localhost":
            self.configuration["server"] = "127.0.0.1"          # use it hard coded since getting the IP with socket.gethostbyname(socket.gethostname()) gives "127.0.1.1" what should be OK but doesn't work!?
        self.client.connect(self.configuration["server"], self.configuration["port"], 60 )

        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        _MOSQUITTO_INITIAL_TIMEOUT = 2

        if len(self.GlobalSubscribedTopics):
            self.timer(name = self._MOSQUITTO_SUBSCRIBE_TIMER_NAME, reSetup = True, timeout = _MOSQUITTO_INITIAL_TIMEOUT)

        self.InitialConnected = True

        self.logger.info(self, f"MQTT connected with result code " + str(rc))

    def on_message(self, client, userdata, msg):
        tempTopic = str(msg.topic)
        #print(Supporter.hexAsciiDump(msg.payload))
        #print(Supporter.hexAsciiDump(tempTopic))
        tempMsg = str(Supporter.decode(msg.payload))

        self.logger.debug(self, f"MQTT message received: {tempMsg} from {tempTopic}")

        self.mqttPublish(tempTopic, tempMsg, globalPublish = True, enableEcho = False)
        #Supporter.debugPrint(f"ON_MESSAGE: {tempTopic}, {tempMsg}", color = "RED")

    def handleQueueOverflow(self):
        # if there was no on_connect so far and our mqttRxQueue is filled up at a level of 90% we will try to clear the loop at least even if messages get lost

        printError = False
        while self.mqttRxQueue.qsize() >= (self.QUEUE_SIZE * 0.9):
            self.mqttRxQueue.get(block = False)      # read a message
            printError = True

        if printError:
            self.logger.error(self, "MQTT RX queue was quiet full. We loss Messages!")

    def threadInitMethod(self):
        self.GlobalSubscribedTopics = []
        self.BridgeTopic = self.createOutTopic(self.createProjectTopic(self.configuration["internalBridge"]))

        # subscribe internally global to get all global msg
        self.mqttSubscribeTopic("#", globalSubscription = True)

        self.InitialConnected = False

        tries = 0
        while tries < self.MAX_INIT_TRIES:
            self.handleQueueOverflow()
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

        self.handleQueueOverflow()

        # if timer was setup in onConnect() we resubscribe all topics here 
        if self.timerExists(self._MOSQUITTO_SUBSCRIBE_TIMER_NAME):
            if self.timer(self._MOSQUITTO_SUBSCRIBE_TIMER_NAME, oneShot = True):
                for topic in self.GlobalSubscribedTopics:
                    self.client.subscribe(topic)

        if self.InitialConnected:
            while not self.mqttRxQueue.empty():
                newMqttMessageDict = self.readMqttQueue(error = False)
    
                # If messageType == Publish we have to publish The Data to MQTT Broker
                if newMqttMessageDict["global"]:
                    self.logger.debug(self, " received global queue message :" + str(newMqttMessageDict))
                    try:
                        self.client.publish(newMqttMessageDict["topic"], json.dumps(newMqttMessageDict["content"]), retain = self.configuration["sendRetained"])
                        #Supporter.debugPrint(f"PUBLISH: {newMqttMessageDict['topic']}, {newMqttMessageDict['content']}", color = "RED")
                    except:
                        self.logger.error(self, f"Could not send MQTT msg to broker: {str(newMqttMessageDict)}")
                elif newMqttMessageDict["topic"] == self.BridgeTopic:
                    if MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE in newMqttMessageDict["content"]:
                        try:
                            self.GlobalSubscribedTopics.remove(newMqttMessageDict["content"][MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE])
                        except:
                            self.logger.error(self, f'Could not find topic in locally list: {newMqttMessageDict["content"][MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE]}')
                        try:
                            self.client.unsubscribe(newMqttMessageDict["content"][MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE])
                            self.logger.info(self, f'Unsubscribed globally: {newMqttMessageDict["content"][MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE]}')
                        except:
                            self.logger.error(self, f'Could not unsubscribe globally: {newMqttMessageDict["content"][MqttBridge.GLOBAL_UNSUBSCRIBER_MESSAGE]}')
                    elif MqttBridge.GLOBAL_SUBSCRIBER_MESSAGE in newMqttMessageDict["content"]:
                        try:
                            self.GlobalSubscribedTopics.append(newMqttMessageDict["content"][MqttBridge.GLOBAL_SUBSCRIBER_MESSAGE])
                            self.client.subscribe(newMqttMessageDict["content"][MqttBridge.GLOBAL_SUBSCRIBER_MESSAGE])
                            self.logger.info(self, f'Subscribed globally: {newMqttMessageDict["content"][MqttBridge.GLOBAL_SUBSCRIBER_MESSAGE]}')
                        except:
                            self.logger.error(self, f'Could not subscribe globally: {newMqttMessageDict["content"][MqttBridge.GLOBAL_SUBSCRIBER_MESSAGE]}')
                elif newMqttMessageDict["topic"] == self.createInTopic(self.getObjectTopic()):
                    # check here msg for class Mosquitto
                    self.logger.debug(self, " received queue message :" + str(newMqttMessageDict))
        else:
            self._mqttRxQueueGetIgnoreOnce = True


    def threadBreak(self):
        time.sleep(0.1)


    #def threadTearDownMethod(self):
    #    pass

