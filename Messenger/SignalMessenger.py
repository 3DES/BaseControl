import time
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


