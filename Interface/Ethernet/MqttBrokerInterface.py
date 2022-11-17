import time
import paho.mqtt.client as mqtt
import json 

from Base.InterfaceBase import InterfaceBase
from Base.Supporter import Supporter


class MqttBrokerInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        self.tagsIncluded(["user", "password", "server", "port"])

    def connectMqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.dontCareList = {}
        self.logger.info(self, f"{self.name}: Try to establish MQTT connection")
        self.client.username_pw_set(self.configuration["user"], self.configuration["password"])
        self.client.connect(self.configuration["server"], self.configuration["port"], 60 )
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(self, f"MQTT connected with result code " + str(rc))

        # Subscribe to projectName/# 
        self.client.subscribe(f"{self.get_projectName()}/#")

    def on_message(self, client, userdata, msg):
        tempTopic = str(msg.topic)
        #print(Supporter.hexAsciiDump(msg.payload))
        #print(Supporter.hexAsciiDump(tempTopic))
        tempMsg = str(Supporter.decode(msg.payload))
        self.logger.info(self, f"MQTT message received: {tempMsg} from {tempTopic}")
        # if topic and msg is in dontCareList we will ignore the msg
        # we have to check first if topic is in the list
        if tempTopic in self.dontCareList:
            if self.dontCareList[tempTopic] == tempMsg:
                del self.dontCareList[tempTopic]
            else:
                self.mqttPublish(tempTopic, tempMsg, globalPublish = True, enableEcho = False)

    def threadInitMethod(self):
        # subscribe internally global to get all global msg
        self.mqttSubscribeTopic(self.get_projectName() + "/#", globalSubscription = True)
        try:
            # Try to connect to MQTT server, there could be a exception if ethernet or server is not available
            self.connectMqtt()
        except:
            self.logger.warning(self, "Could not establish initial MQTT connection")
            # @todo nach einer Zeit wieder probieren Es gibt eine exception wenn kein LAN oder ethernet verfugbar ist
            # RECONNECT_DELAY_SET(min_delay=1, max_delay=120)

    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            
            # If messageType == Publish we have to publish The Data to MQTT Broker
            if newMqttMessageDict["global"]:
                self.logger.info(self, " received global queue message :" + str(newMqttMessageDict))
                try:
                    self.client.publish(newMqttMessageDict["topic"], newMqttMessageDict["content"], retain = True)
                    # we remember the msg to ignore incomming own msg
                    self.dontCareList[newMqttMessageDict["topic"]] = newMqttMessageDict["content"]
                except:
                    self.logger.error(self, "Could not send MQTT msg to broker: "  + str(newMqttMessageDict))
            elif newMqttMessageDict["topic"] == self.createInTopic(self.getObjectTopic()):
                # check here msg for class Mosquitto
                self.logger.info(self, " received queue message :" + str(newMqttMessageDict))


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

