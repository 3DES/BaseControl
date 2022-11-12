from datetime import datetime


def baseTests():
    from Base.Base import Base
    from Base.Supporter import Supporter

    myBase = Base("myByse", {})

    while True:
        myBase = Base("XX", {})
        if myBase.timer("T1", timeout = 5, firstTimeTrue = True):
            if not hasattr(myBase, "msgCtr1"):
                myBase.msgCtr1 = 0
            myBase.msgCtr1 += 1
            print(f"TIMING EVENT T1: {myBase.msgCtr1} {Supporter.getTimeStamp()}")



'''
Test main function
'''
if __name__ == '__main__':
    baseTests()

