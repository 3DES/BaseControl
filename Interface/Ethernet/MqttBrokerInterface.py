import time
import paho.mqtt.client as mqtt
import json 

from Base.InterfaceBase import InterfaceBase

class MqttBrokerInterface(InterfaceBase):
    '''
    classdocs
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)
        pass

    def connectMqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.logger.info(self, f"{self.name}: Try to establish MQTT connection")
        self.client.username_pw_set(self.configuration["user"], self.configuration["password"])
        self.client.connect(self.configuration["server"], self.configuration["port"], 60 )
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(self, f"MQTT connected with result code " + str(rc))
        
        # Subscribe eiter to projectName/# or projectName/in/#
        if self.configuration["transmitAllExternalMessages"]:
            self.client.subscribe(f"{self.get_projectName()}/#")
        else:
            self.client.subscribe(f"{self.get_projectName()}/+/in/#")

    def on_message(self, client, userdata, msg):
        tempTopic = str(msg.topic)
        tempMsg = str(msg.payload.decode())
        self.logger.info(self, f"MQTT message received: {tempMsg} from {tempTopic}")
        self.mqttPublish(tempTopic, tempMsg, globalPublish = True, enableEcho = False)

    def threadInitMethod(self):
        # subscribe internally global to get global msg
        self.mqttSubscribeTopic(self.createInTopic(self.getObjectTopic()), globalSubscription = True)
        try:
            # Try to connect to MQTT server, there could be a exception if ethernet or server is not available
            self.connectMqtt()
        except:
            self.logger.warning(self, f"Could not establish initial MQTT connection")
            # @todo nach einer Zeit wieder probieren Es gibt eine exception wenn kein LAN oder ethernet verfugbar ist
            # RECONNECT_DELAY_SET(min_delay=1, max_delay=120)

    def threadMethod(self):
        while not self.mqttRxQueue.empty():
            newMqttMessageDict = self.mqttRxQueue.get(block = False)      # read a message
            self.logger.info(self, f" received queue message :" + str(newMqttMessageDict))
            
            # If messageType == Publish we have to publish The Data to MQTT Broker
            if newMqttMessageDict["global"]:
                try:
                    self.client.publish(newMqttMessageDict["topic"], json.dumps(newMqttMessageDict["content"]), retain = False)
                except:
                    self.logger.error(self, "Could not send MQTT msg to broker: %s to %s" (newMqttMessageDict["content"], newMqttMessageDict["topic"]))


    #def threadBreak(self):
    #    pass


    #def threadTearDownMethod(self):
    #    pass

