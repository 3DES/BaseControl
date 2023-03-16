import serial
import time
import sys
from datetime import datetime



def checksum(bytes):
    chk = 0
    for b in _cmd:
        chk += b
    chk &= 0xFF
    chk = f"{chk:02X}"
    chk = bytes.fromhex(chk)
    return chk


def write(serialIF, data, info):
    bytes_written = serialIF.write(data)
    print(f"{info} wrote #{bytes_written} ({timestamp()}): {data}")
    time.sleep(int(pause))


def timestamp():
    return datetime.timestamp(datetime.now())


def timestamp_delta(ts):
    return timestamp() - ts



## Vars ################
port = "COM3"
baud = 9600
pause = 5
reset = False
readOnly = False
########################

if len(sys.argv) >= 2:
    port = sys.argv[1]
if len(sys.argv) >= 3:
    pause = sys.argv[2]
if len(sys.argv) >= 4:
    if sys.argv[3]:
        reset = True
if len(sys.argv) >= 5:
    if sys.argv[4]:
        readOnly = True
print(f"port is {port}, pause is {pause}")

## Command components ???
startFlag = bytes.fromhex("A5")
moduleAddress = bytes.fromhex("80")
commandID = bytes.fromhex("90")
dataLength = bytes.fromhex("08")
data = bytes.fromhex("00" * 8)  

####
_resetCmd = startFlag + moduleAddress + bytes.fromhex("00") + dataLength + data
_cmd      = startFlag + moduleAddress + commandID           + dataLength + data
resetCmd  = _resetCmd + checksum(_resetCmd)
cmd       = _cmd + checksum(_cmd)
#print (f"command {cmd}")
#print (f"reset command {resetCmd}")


with serial.serial_for_url(port, baud) as s:
    s.timeout = 1
    s.write_timeout = 1

    if reset:
        s.flushInput()
        s.flushOutput()
        write(s, resetCmd, "reset command")

    s.flushInput()
    s.flushOutput()
    write(s, cmd, "command")

    for _ in range(100000):
        response_line = b""
        ts = timestamp()
        while not len(response_line) >= 13 and not timestamp_delta(ts) > 5:
            data = s.read(13)
            if len(data):
                response_line += data

        print (f"Got response: {response_line}")
        if len(response_line) < 13:
            s.flushInput()
            s.flushOutput()
            write(s, resetCmd, "reset command")
        
        time.sleep(int(pause))
        write(s, cmd, "command")

