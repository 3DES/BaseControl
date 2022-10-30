from Base.Supporter import Supporter


class InterfaceFactory(object):
    '''
    classdocs
    '''


    @classmethod
    def createInterface(cls, masterName : str, configuration : dict) -> list:
        '''
        Creates an interface from given configuration
        '''
        interfaceList = []
        
        for interfaceName in configuration: 
            # create interface name
            interfaceConfiguration = configuration[interfaceName]
            if "connection" not in interfaceConfiguration:
                raise Exception("interface definition needs key \"connection\" " + str(interfaceConfiguration)) 

            interfaceThreadName = masterName + "_" + interfaceName
            

            # create interface and store it to return list so creator can subscribe to all of them
            fullClassName = interfaceConfiguration["connection"]
            loadableClass = Supporter.loadClassFromFile(fullClassName)
            interfaceList.append(loadableClass(interfaceThreadName, configuration))

        return interfaceList
