import unittest
import mock
import GridLoad.EasyMeter
import Base.Supporter
from pickle import FALSE


# execute tests in pydev Ctrl+F9, for debugger press shift while double-click the test case
class EasyMeterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        '''
        Set up parameters only allowed to be set up once
        '''
        GridLoad.EasyMeter.EasyMeter.set_projectName("myProject")       # only allowed once
    

    configuration = {
        "conservativeDelta" : 0,
        "progressiveDelta"  : 0,
        "loadCycle"         : 15 * 60,
        "gridLossThreshold" : 60,
        "messageInterval"   : 60,
        "minimumPowerStep"  : 100,
    }


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def setUp(self, mock_parent):
        '''
        Set up values that have to be set up for each test case
        '''
        #GridLoad.EasyMeter.EasyMeter.set_projectName("myProject")       # only allowed once
        self.name = "myThread"
        GridLoad.EasyMeter.EasyMeter.configuration = self.configuration     # inject configuration
        GridLoad.EasyMeter.EasyMeter.name          = self.name              # inject name
        self.easyMeter = GridLoad.EasyMeter.EasyMeter(self.name, self.configuration)


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
            "conservativeDelta" : self.configuration["conservativeDelta"],
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
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
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
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
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
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
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
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameters6(self, mock_parent):
        '''
        Check that __init__ expects certain values
        finally all needed parameters are contained, so no exception should be thrown
        '''
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
            "messageInterval"   : self.configuration["messageInterval"],
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues1(self, mock_parent):
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
            "messageInterval"   : self.configuration["loadCycle"],                  # <-- error value
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues2(self, mock_parent):
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
            "messageInterval"   : self.configuration["loadCycle"] / 2 - 1,          # <-- error value
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues3(self, mock_parent):
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["loadCycle"],                  # <-- error value
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
            "messageInterval"   : self.configuration["messageInterval"],          
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues4(self, mock_parent):
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : -1,                                               # <-- error value
            "minimumPowerStep"  : self.configuration["minimumPowerStep"],
            "messageInterval"   : self.configuration["messageInterval"],          
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    def test_init_parameterValues5(self, mock_parent):
        configuration = {
            "conservativeDelta" : self.configuration["conservativeDelta"],
            "progressiveDelta"  : self.configuration["progressiveDelta"],
            "loadCycle"         : self.configuration["loadCycle"],
            "gridLossThreshold" : self.configuration["gridLossThreshold"],
            "minimumPowerStep"  : 10,                                               # <-- error value
            "messageInterval"   : self.configuration["messageInterval"],          
        }
        GridLoad.EasyMeter.EasyMeter.configuration = configuration
        with self.assertRaises(Exception):
            GridLoad.EasyMeter.EasyMeter(self.name, None)


    @mock.patch("GridLoad.EasyMeter.ThreadObject.__init__", autospec=True)
    #@mock.patch("GridLoad.EasyMeter.Supporter.getTimeStamp", autospec=True)
    def test_prepareNewEasyMeterMessage(self, mock_parent):
        '''
        '''
        # test prepareNewEasyMeterMessage()
        self.easyMeter.energyProcessData["backedupEnergyLevel"] = 0
        self.easyMeter.energyProcessData["currentEnergyLevel"] = 0
        self.easyMeter.energyProcessData["lastEnergyLevel"] = 0
        self.easyMeter.gridLossDetected = True
        self.easyMeter.lastEasyMeterMessageTime = 0

        mock_calculateNewPowerLevel = mock.Mock()
        GridLoad.EasyMeter.EasyMeter.calculateNewPowerLevel = mock_calculateNewPowerLevel 
        powerLevels = [(0, 1000), (1000, 500), (3000, 500), (3050, 500), (4000, 500), (1500, 1000), (0, 1000), (50, 500), (0, 1000), (5000, 500), (0, 1000), (0, 1000)] 
        mock_calculateNewPowerLevel.side_effect = powerLevels

        mock_getTimeStamp = mock.Mock()
        day = 15
        hour = 10
        messageTime = [Base.Supporter.Supporter.getTimeOfToday(year = 2020, month = 5, day = 15, hour = hour, minute = 8, second = 0)]
        for timeStep in range(20):
            minute = 15 * (1 + timeStep)
            hour  += minute // 60
            minute = minute % 60
            day   += hour // 24
            hour   = hour % 24
            messageTime.append(Base.Supporter.Supporter.getTimeOfToday(year = 2020, month = 5, day = 15, hour = hour, minute = minute, second = 0))
        mock_getTimeStamp.side_effect = messageTime
        GridLoad.EasyMeter.Supporter.getTimeStamp = mock_getTimeStamp 

        index = 0
        with self.subTest(f"first startup or OFF message received {powerLevels[index]}"):
            '''
            Should stay with power level == 0
            '''
            self.easyMeter.energyData["previousPower"] = 9999
            self.easyMeter.energyData["previousReduction"] = 9999
            self.easyMeter.energyData["previousTimestamp"] = 9999
            self.easyMeter.energyProcessData["gridLossDetected"] = True
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()
    
            self.assertEqual(self.easyMeter.energyData["previousPower"], 0)
            self.assertEqual(self.easyMeter.energyData["previousReduction"], 0) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], 0) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 1000
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 3000
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should stay at power level == 3000
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           
            
            self.easyMeter.prepareNewEasyMeterMessage()
            
            # value ignored, so all values must be previous values and "updatePowerValue" must be False
            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 2][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 2][1])
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 2]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index - 1][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertFalse(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 4000
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 2][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 2][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 2]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 1500
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 0
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should stay at power level == 0
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            # value ignored, so all values must be previous values and "updatePowerValue" must be False
            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 2][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 2][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 2]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index - 1][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index - 1])
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertFalse(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should stay at power level == 0
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            # power level == 0 is always taken over and set for safety reasons!
            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 2][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 2][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 2]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 5000
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should switch to power level == 0
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 

        index += 1
        with self.subTest(f"message from easy meter with power level {powerLevels[index]}"):
            '''
            Should stay at power level == 0
            '''
            self.easyMeter.energyProcessData["gridLossDetected"] = True     # only to check it's cleared
            self.easyMeter.energyData["updatePowerValue"] = False           

            self.easyMeter.prepareNewEasyMeterMessage()

            self.assertEqual(self.easyMeter.energyData["previousPower"], powerLevels[index - 1][0])
            self.assertEqual(self.easyMeter.energyData["previousReduction"], powerLevels[index - 1][1]) 
            self.assertEqual(self.easyMeter.energyData["previousTimestamp"], messageTime[index - 1]) 
            self.assertEqual(self.easyMeter.energyData["allowedPower"], powerLevels[index][0]) 
            self.assertEqual(self.easyMeter.energyData["allowedReduction"], powerLevels[index][1]) 
            self.assertEqual(self.easyMeter.energyData["allowedTimestamp"], messageTime[index]) 
            self.assertEqual(self.easyMeter.energyProcessData["currentEnergyTimestamp"], messageTime[index]) 
            self.assertTrue(self.easyMeter.energyData["updatePowerValue"])
            self.assertFalse(self.easyMeter.energyProcessData["gridLossDetected"]) 




'''
Test main function
'''
if __name__ == '__main__':
    #baseTests()
    EasyMeterTest()

