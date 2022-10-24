import time


from L.L import L
from Worker.W import W
from WD.WD import WD
from Base.SilentBase.TI import TI


w = W("my worker")
wd = WD("my watchdog")
logger = L("my logger")
L.x("main")

print("START")
TI.overallRunning = True

while (TI.workerThreadException is not None):
    time.sleep(0.1)

if TI.workerThreadException is not None:
    print("EXCEPTION")
else:
    print("END")

print("STOP")
TI.stopAllWorkers()
