from Base.InterfaceBase import InterfaceBase


import socket


class TcpInterface(InterfaceBase):
    '''
    TcpInterface blocks when it reads from sock.recv, so watch dog monitoring is not possible for this kind of interface!
    '''


    def __init__(self, threadName : str, configuration : dict):
        '''
        Constructor
        '''
        super().__init__(threadName, configuration)

        # check and prepare mandatory parameters
        self.tagsIncluded(["messageLength", "port"], intIfy = True)
        self.tagsIncluded(["server"])

    
    def threadInitMethod(self):
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        self.server_address = (self.configuration["server"], self.configuration["port"])       # @todo interface bauen und hier verwenden!!! daten dann in init.json schreiben
        self.logger.info(self, 'connecting to %s port %s' % self.server_address)
        self.sock.connect(self.server_address)


    def readSocket(self):
        return self.sock.recv(4096)             # sock.recv will come back as soon as data has been received so the buffer should large enough to receive a whole message


    def readData(self):
        '''
        Can be overwritten, e.g. to collect data until a whole message has been received
        '''
        return self.readSocket()


    def threadMethod(self):
        data = self.readData()
        self.mqttPublish(self.createOutTopic(self.getObjectTopic()), data)


    def threadBreak(self):
        # no need to be nice since the sock.recv already blocks
        pass


    #def threadTearDownMethod(self):
    #    pass

