import unittest
import mock
import GridLoad.EasyMeter
# execute tests in pydev Ctrl+F9, for debugger press shift while double-click the test case
class MyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        '''
        Set up parameters only allowed to be set up once
        '''
        GridLoad.EasyMeter.EasyMeter.set_projectName("myProject")       # only allowed once
    
    
    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def setUp(self, mock_parent):
        '''
        Set up values that have to be set up for each test case
        '''
        #GridLoad.EasyMeter.EasyMeter.set_projectName("myProject")       # only allowed once
        self.name = "myThread"
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
            "gridLossThreshold" : 60,
            "messageInterval"   : 60,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        self.easyMeter = GridLoad.EasyMeter.EasyMeter(self.name, configuration)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_set_projectName(self, mock_parent):
        '''
        Set project name a second time should throw an exception
        '''
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter.set_projectName("myProject")


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters1(self, mock_parent):
        '''
        Check that __init__ expects certain values
        '''
        configuration = {
            "conservativeDelta" : 0,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters2(self, mock_parent):
        '''
        Check that __init__ expects certain values
        '''
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters3(self, mock_parent):
        '''
        Check that __init__ expects certain values
        '''
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)

        
    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters4(self, mock_parent):
        '''
        Check that __init__ expects certain values
        '''
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
            "gridLossThreshold" : 60,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)
        

        
    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters5(self, mock_parent):
        '''
        Check that __init__ expects certain values
        finally all needed parameters are contained, so no exception should be thrown
        '''
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
            "gridLossThreshold" : 60,
            "messageInterval"   : 60,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues(self, mock_parent):
        configuration = {
            "conservativeDelta" : 0,
            "progressiveDelta"  : 0,
            "loadCycle"         : 15 * 60,
            "gridLossThreshold" : 60,
            "messageInterval"   : 15 * 60,
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_prepareNewEasyMeterMessage(self, mock_parent):
        '''
        '''
        # test prepareNewEasyMeterMessage()
        self.easyMeter.energyValues[self.easyMeter.ENERGY_VALUE_NAMES["backedupEnergyLevel"]] = 0
        self.easyMeter.energyValues[self.easyMeter.ENERGY_VALUE_NAMES["currentEnergyLevel"]] = 0
        self.easyMeter.energyValues[self.easyMeter.ENERGY_VALUE_NAMES["lastSentEnergyValue"]] = 0
        self.easyMeter.gridLossDetected = False
        self.easyMeter.lastEasyMeterMessageTime = 0

        self.easyMeter.prepareNewEasyMeterMessage()

        self.assertEqual(self.easyMeter.energyData["previousPower"], 0)
        self.assertEqual(self.easyMeter.energyData["previousReduction"], 0) 
        self.assertEqual(self.easyMeter.energyData["previousTimestamp"], 0) 
        self.assertEqual(self.easyMeter.energyData["allowedPower"], 0) 
        self.assertEqual(self.easyMeter.energyData["allowedReduction"], 0) 
        self.assertNotEqual(self.easyMeter.energyData["allowedTimestamp"], 0) 
        self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
        self.assertFalse(self.easyMeter.gridLossDetected) 
        self.assertNotEqual(self.easyMeter.lastEasyMeterMessageTime, 0)


'''
Test main function
'''
if __name__ == '__main__':
    #baseTests()
    EasyMeterTest()

