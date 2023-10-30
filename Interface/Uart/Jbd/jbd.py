#!/usr/bin/env python

# BMS Tools
# Copyright (C) 2020 Eric Poulsen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import serial
import time
import struct
import threading
import queue
import sys
from enum import Enum
from functools import partial
from . import persist

from .registers import (BaseReg, Unit, DateReg, IntReg, 
                        TempReg, TempRegRO, DelayReg, UsePasswordReg,
                        SetPasswordReg, ScDsgoc2Reg, CxvpHighDelayScRelReg,
                        BitfieldReg, StringReg, ErrorCountReg, BasicInfoReg, 
                        BasicInfoRegUpSeries,
                        CellInfoReg, DeviceInfoReg, ReadOnlyException)

__all__ = 'JBD'

class BMSError(Exception): pass
class BMSPasswordError(BMSError): pass

class JBD:
    START               = 0xDD
    END                 = 0x77
    READ                = 0xA5
    WRITE               = 0x5A

    REG_BYTE            = 1
    OK_BYTE             = 2
    HEADER_LENGTH       = 3
    FACTORY_MOD_CMD     = [0x56, 0x78]

    CELL_CAL_REG_START  = 0xB0
    CELL_CAL_REG_END    = 0xCF

    NTC_CAL_REG_START   = 0xD0
    NTC_CAL_REG_END     = 0xD7

    I_CAL_IDLE_REG      = 0xAD
    I_CAL_CHG_REG       = 0xAE
    I_CAL_DSG_REG       = 0xAF

    FACTORY_MOD_REG     = 0x00
    RESET_PASSWORD_REG  = 0x09
    USE_PASSWORD_REG    = 0X06
    SET_PASSWORD_REG    = 0X07
    CHG_DSG_EN_REG      = 0xE1
    BAL_CTRL_REG        = 0xE2

    CAP_REM_REG         = 0xE0


    def __init__(self, s, timeout = 1, debug = False):
        self.s = s
        try:
            self.s.close()
            s.timeout=0.5
        except: 
            pass
        self._open_cnt = 0
        self._lock = threading.RLock()
        self._dbgTime = 0
        self.timeout = timeout
        self.password = bytes(6)
        self.debug = debug
        self.writeNVMOnExit = False
        self.bkgReadThread = None
        self.serialAlwaysOpen = False
        self.bkgReadQ = queue.Queue()

        self.eeprom_regs = [
            ### EEPROM settings
            ## Settings
            # Basic Parameters
            IntReg('covp', 0x24, Unit.MV, 1),
            IntReg('covp_rel', 0x25, Unit.MV, 1),
            IntReg('cuvp', 0x26, Unit.MV, 1),
            IntReg('cuvp_rel', 0x27, Unit.MV, 1),
            IntReg('povp', 0x20, Unit.MV, 10),
            IntReg('povp_rel', 0x21, Unit.MV, 10),
            IntReg('puvp', 0x22, Unit.MV, 10),
            IntReg('puvp_rel', 0x23, Unit.MV, 10),
            TempReg('chgot', 0x18),
            TempReg('chgot_rel', 0x19),
            TempReg('chgut', 0x1a),
            TempReg('chgut_rel', 0x1b),
            TempReg('dsgot', 0x1c),
            TempReg('dsgot_rel', 0x1d),
            TempReg('dsgut', 0x1e),
            TempReg('dsgut_rel', 0x1f),
            IntReg('chgoc', 0x28, Unit.MA, 10),
            IntReg('dsgoc', 0x29, Unit.MA, 10),
            DelayReg('cell_v_delays', 0x3d, 'cuvp_delay', 'covp_delay'),
            DelayReg('pack_v_delays', 0x3c, 'puvp_delay', 'povp_delay'),
            DelayReg('chg_t_delays', 0x3a, 'chgut_delay', 'chgot_delay'),
            DelayReg('dsg_t_delays', 0x3b, 'dsgut_delay', 'dsgot_delay'),
            DelayReg('chgoc_delays', 0x3e, 'chgoc_delay', 'chgoc_rel'),
            DelayReg('dsgoc_delays', 0x3f, 'dsgoc_delay', 'dsgoc_rel'),

            # High Protection Configuration
            IntReg('covp_high', 0x36, Unit.MV, 1),
            IntReg('cuvp_high', 0x37, Unit.MV, 1),
            ScDsgoc2Reg('sc_dsgoc2', 0x38),
            CxvpHighDelayScRelReg('cxvp_high_delay_sc_rel', 0x39),

            # Function Configuration
            BitfieldReg('func_config', 0x2d, 'switch', 'scrl', 'balance_en', 'chg_balance_en', 'led_en', 'led_num'),

            # NTC Configuration
            BitfieldReg('ntc_config', 0x2e, *(f'ntc{i+1}' for i in range(8))),

            # Balance Configuration
            IntReg('bal_start', 0x2a, Unit.MV, 1),
            IntReg('bal_window', 0x2b, Unit.MV, 1),

            # Other Configuration
            IntReg('shunt_res', 0x2c, Unit.MO, .1),
            IntReg('cell_cnt', 0x2f, int, 1),
            IntReg('cycle_cnt', 0x17, int, 1),
            IntReg('serial_num', 0x16, int, 1),
            StringReg('mfg_name', 0xa0),
            StringReg('device_name', 0xa1),
            StringReg('barcode', 0xa2),
            DateReg('mfg_date', 0x15),

            # Capacity Config
            IntReg('design_cap', 0x10, Unit.MAH, 10), 
            IntReg('cycle_cap', 0x11, Unit.MAH, 10),
            IntReg('dsg_rate', 0x14, Unit.PCT, .1), # presuming this means rate of self-discharge
            IntReg('cap_100', 0x12, Unit.MV, 1), # AKA "Full Chg Vol"
            IntReg('cap_80', 0x32, Unit.MV, 1),
            IntReg('cap_60', 0x33, Unit.MV, 1),
            IntReg('cap_40', 0x34, Unit.MV, 1),
            IntReg('cap_20', 0x35, Unit.MV, 1),
            IntReg('cap_0', 0x13, Unit.MV, 1), # AKA "End of Dsg VOL"
            IntReg('fet_ctrl', 0x30, Unit.S, 1),
            IntReg('led_timer', 0x31, Unit.S, 1),

            # Errors
            ErrorCountReg('error_cnts', 0xaa),
        ]
        self.eeprom_reg_by_valuename = {}
        self.eeprom_reg_by_adx = {}
        self.eeprom_reg_by_regname = {}
        for reg in self.eeprom_regs:
            map = {k:reg for k in reg.valueNames}
            self.eeprom_reg_by_valuename.update(map)
            self.eeprom_reg_by_adx[reg.adx] = reg
            self.eeprom_reg_by_regname[reg.regName] = reg


        self.basicInfoReg = BasicInfoReg('basic_info', 0x03)
        self.cellInfoReg = CellInfoReg('cell_info', 0x04)
        self.deviceInfoReg = DeviceInfoReg('device_info', 0x05)

    @staticmethod
    def toHex(data):
        return ' '.join([f'{i:02X}' for i in data])

    def dbgPrint(self, *args, **kwargs):
        kwargs['file'] = sys.stderr
        if self.debug:
            args = list(args)
            now = time.time()
            elapsed = now - self._dbgTime if self._dbgTime else 0
            args.insert(0, f'[{elapsed:.3f}]')
            print(*args, **kwargs)
            self._dbgTime = now

    @property
    def serial(self):
        return self.s
    
    @serial.setter
    def serial(self, s):
        s.timeout = .25
        self.s = s 

    def open(self):
        if self.serialAlwaysOpen and self._open_cnt > 0:
            return
        if self.bkgReadThread:
            return
        self._lock.acquire()
        self._open_cnt += 1
        if self._open_cnt == 1:
            self.s.open()
    
    def close(self):
        if self.serialAlwaysOpen:
            return
        if self.bkgReadThread:
            return
        if not self._open_cnt: 
            return
        self._open_cnt -= 1
        self._lock.release()
        if not self._open_cnt:
            self.s.close()

    @staticmethod
    def chksum(payload):
        return 0x10000 - sum(payload)

    def extractPayload(self, data):
        payloadStart = self.HEADER_LENGTH + 1
        assert len(data) >= 7
        datalen = data[self.HEADER_LENGTH]
        data = data[payloadStart:payloadStart+datalen]
        self.dbgPrint('extractPayload returning', self.toHex(data))
        return data

    def cmd(self, op, reg, data):
        payload = [reg, len(data)] + list(data)
        chksum = self.chksum(payload)
        data = [self.START, op] + payload + [chksum, self.END]
        format = f'>BB{len(payload)}BHB'
        return struct.pack(format, *data) 

    def readCmd(self, reg, data  = []):
        return self.cmd(self.READ, reg, data)

    def writeCmd(self, reg, data = []):
        return self.cmd(self.WRITE, reg, data)

    def bkgReadWorker(self):
        self.dbgPrint('bkgReadWorker started')
        while self.bkgReadRun:
            ok, reg, payload = self._readPacket()
            if ok:
                # cust FW debug packet reg
                if reg == 0xFE:
                    try:
                        payload = str(payload, 'utf-8')
                        print('dbg >', payload)
                    except:
                        print(' '.join([f'{i:02X}' for i in payload]))
                else:
                    self.bkgReadQ.put((ok, payload))
        self.dbgPrint('bkgReadWorker terminated')

    #primarily for firmware debugging; not used by normal GUI
    @property
    def bkgRead(self):
        return bool(self.bkgReadThread)

    @bkgRead.setter
    def bkgRead(self, enable):
        if enable:
            if not self.bkgReadThread:
                while not self.bkgReadQ.empty():
                    self.bkgReadQ.get()
                self.bkgReadRun = True
                self.bkgReadThread = threading.Thread(target = self.bkgReadWorker)
                self.s.open()
                self.bkgReadThread.start()
        else:
            if self.bkgReadThread:
                self.bkgReadRun = False
                self.bkgReadThread.join(5)
                if self.bkgReadThread.is_alive():
                    self.dbgPrint('bkgReadThread did not join')
                else:
                    self.dbgPrint('bkgReadThread successfully joined')
                self.s.close()
                self.bkgReadThread = None

    def _readPacket(self, timeout = None):
        t = timeout if timeout is not None else self.timeout
        then = time.time() + t
        #self.dbgPrint(f'timeout is {t}')
        d = []
        msgLen = 0
        complete = False
        while then > time.time():
            byte = self.s.read()
            if not byte: 
                continue
            #self.dbgPrint(f'raw rx byte: {byte}')
            byte = byte[0]
            if not d and byte != self.START: continue
            then = time.time() + t
            d.append(byte)
            if len(d) == self.HEADER_LENGTH + 1:
                msgLen = d[-1]
            if byte == self.END and len(d) >= 7 + msgLen: 
                complete = True
                break
        if d and complete:
            self.dbgPrint('readPacket:', self.toHex(d))
            reg = d[self.REG_BYTE]
            ok = not d[self.OK_BYTE]
            return ok, reg, self.extractPayload(bytes(d))
        self.dbgPrint(f'readPacket failed with {len(d)} bytes')
        return False, None, None

    def readPacket(self):
        if self.bkgReadThread: # mostly FW debugging
            try:
                ok, payload = self.bkgReadQ.get(timeout = self.timeout)
                return ok, payload
            except queue.Empty:
                return False, None
        else: # normal path
            then = time.time() + self.timeout
            
            while(time.time() < then):
                ok, reg, payload = self._readPacket()
                # cust FW debug packet reg
                if reg != 0xFE:
                    break
            return ok, payload

    def writeCmdWaitResp(self, adx, payload):
        return self._sendCmdWaitResp(adx, payload, False)

    def readCmdWaitResp(self, adx, payload):
        return self._sendCmdWaitResp(adx, payload, True)

    def _sendCmdWaitResp(self, adx, payload, read):
        if read:
            cmd = self.readCmd(adx, payload)
        else:
            cmd = self.writeCmd(adx, payload)

        try:
            self.open()
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            return payload
        finally:
            self.close()

    def __enter__(self):
        self.open()
        try:
            self.enterFactory()
        except:
            self.close()
            raise

    def __exit__(self, type, value, traceback):
        try:
            self.exitFactory(self.writeNVMOnExit)
            self.writeNVMOnExit = False
        finally:
            self.close()

    def factoryContext(self, writeNVMOnExit = False):
        self.writeNVMOnExit = writeNVMOnExit 
        return self

    def enterFactory(self):
        try:
            self.open()
            if 1:
                cnt = 5
                while cnt:
                    try:
                        self._sendPassword()
                        break
                    except Exception as e:
                        self.dbgPrint(f'password exception {repr(e)}')
                    cnt -= 1
                    time.sleep(.3)
                else:
                    raise BMSPasswordError('bad password')

            cnt = 5
            while cnt:
                cmd = self.writeCmd(self.FACTORY_MOD_REG, self.FACTORY_MOD_CMD)
                self.s.write(cmd)
                ok, x = self.readPacket()
                if ok and x is not None: # empty payload is valid
                    self.dbgPrint('enter factory: success')
                    return x
                self.dbgPrint('enter factory: no response')
                cnt -= 1
                time.sleep(.3)
            return False
        finally:
            self.close()

    def exitFactory(self, writeNVM = False):
        try:
            self.open()
            cmd = self.writeCmd(1,  [0x28, 0x28] if writeNVM else [0,0])
            self.s.write(cmd)
            ok, d = self.readPacket()
            return ok
        finally:
            self.close()

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        assert len(value) == 6
        if isinstance(value, str):
            self._password = bytes(value, 'utf-8')
        else:
            self._password = bytes(value)

    def _sendPassword(self):
        reg = UsePasswordReg('x', self.USE_PASSWORD_REG)
        reg.set('x', self._password)
        cmd = self.writeCmd(reg.adx, reg.pack())
        self.dbgPrint(f'sendPassword payload is {cmd}')
        self.s.write(cmd)
        ok, payload = self.readPacket()
        if not ok: raise BMSError()
        if payload is None: raise TimeoutError()

    def setPassword(self, password):
        if isinstance(password, str):
            password = bytes(password, 'utf-8')
        with self.factoryContext():
            reg = SetPasswordReg('x', self.SET_PASSWORD_REG)
            reg.set('x', self._password)
            reg.setNewPassword(password)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

        self._password = password

    def clearPassword(self):
        try:
            self.open()
            cnt = 5 
            while cnt:
                try:
                    reg = UsePasswordReg('x', self.RESET_PASSWORD_REG)
                    reg.set('x', b'J1B2D4')
                    cmd = self.writeCmd(reg.adx, reg.pack())
                    self.dbgPrint(f'clearPassword payload {cmd}')
                    self.s.write(cmd)
                    ok, payload = self.readPacket()
                    if not ok: raise BMSError()
                    if payload is None: raise TimeoutError()
                    break
                except:
                    cnt -= 1
        finally:
            self.close()

    def readEeprom(self, progressFunc = None):
        with self.factoryContext():
            ret = {}
            numRegs = len(self.eeprom_regs)
            if progressFunc: progressFunc(0)

            for i, reg in enumerate(self.eeprom_regs):
                cmd = self.readCmd(reg.adx)
                self.s.write(cmd)
                ok, payload = self.readPacket()
                if not ok: raise BMSError()
                if payload is None: raise TimeoutError()
                if progressFunc: progressFunc(int(i / (numRegs-1) * 100))
                reg.unpack(payload)
                ret.update(dict(reg))
            return ret

    def writeEeprom(self, data, progressFunc = None):
        with self.factoryContext(True):
            ret = {}
            numRegs = len(self.eeprom_regs)
            if progressFunc: progressFunc(0)
            regs = set()

            for valueName, value in data.items():
                reg = self.eeprom_reg_by_valuename.get(valueName)
                if not reg: raise RuntimeError(f'unknown valueName {valueName}')
                try:
                    reg.set(valueName, value)
                    regs.add(reg)
                except ReadOnlyException:
                    pass

            for i,reg in enumerate(regs):
                data = reg.pack()
                cmd = self.writeCmd(reg.adx, data)
                self.s.write(cmd)
                ok, payload = self.readPacket()
                if not ok: raise BMSError()
                if payload is None: raise TimeoutError()
                if progressFunc: progressFunc(int(i / (numRegs-1) * 100))

    def readReg(self, reg):
        with self.factoryContext():
            if isinstance(reg, int):
                if reg not in self.eeprom_reg_by_adx:
                    raise ValueError('unknown register address')
                reg = self.eeprom_reg_by_adx[reg]
            elif isinstance(reg, BaseReg):
                pass
            elif isinstance(reg, str):
                if (reg not in self.eeprom_reg_by_regname) and (reg not in self.eeprom_reg_by_valuename):
                    raise ValueError('unknown register name')
                x = self.eeprom_reg_by_regname.get(reg, None)
                if x is None:
                    x = self.eeprom_reg_by_valuename[reg]
                reg = x
            else:
                raise ValueError('reg type must be int or instantce of BaseReg')

            cmd = self.readCmd(reg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            reg.unpack(payload)
            return reg

    def writeReg(self, reg, writeNVM = False):
        with self.factoryContext(writeNVM):
            if not isinstance(reg, BaseReg):
                raise ValueError('reg type must be instantce of BaseReg')

            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def loadEepromFile(self, filename):
        p = persist.JBDPersist()
        with open(filename) as f:
            data = f.read()
        return p.deserialize(data)

    def saveEepromFile(self, filename, data):
        p = persist.JBDPersist()
        with open(filename, 'wb') as f:
            f.write(p.serialize(data))

    def readInfo(self):
        try:
            self.open()
            basic = self.readBasicInfo()
            cell = self.readCellInfo()
            device = self.readDeviceInfo()
            return basic, cell, device
        finally:
            self.close()

    def readBasicInfo(self):
        try:
            self.open()
            cmd = self.readCmd(self.basicInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            self.basicInfoReg.unpack(payload)
            return dict(self.basicInfoReg)
        finally:
            self.close()

    def readCellInfo(self):
        try:
            self.open()
            cmd = self.readCmd(self.cellInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            self.cellInfoReg.unpack(payload)
            return dict(self.cellInfoReg)
        finally:
            self.close()

    def readDeviceInfo(self):
        try:
            self.open()
            cmd = self.readCmd(self.deviceInfoReg.adx)
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            self.deviceInfoReg.unpack(payload)
            return dict(self.deviceInfoReg)
        finally:
            self.close()
    
    def clearErrors(self):
        with self.factoryContext(True):
            pass

    def calCell(self, cells, progressFunc = None):
        'cells is a dict of cell # (base 0) to mV'
        with self.factoryContext():
            cur = 0
            cnt = len(cells)
            for n, v in cells.items():
                adx = self.CELL_CAL_REG_START + n
                if adx > self.CELL_CAL_REG_END: continue
                reg = IntReg('cal', adx, Unit.MV, 1)
                reg.set('cal', v)
                cmd = self.writeCmd(adx, reg.pack())
                self.s.write(cmd)
                ok, payload = self.readPacket()
                if not ok: raise BMSError()
                if payload is None: raise TimeoutError()
                if progressFunc: progressFunc(cur / cnt)
                cur += 1

    def calNtc(self, ntc, progressFunc = None):
        'ntc is a dict of ntc # (base 0) to K'
        with self.factoryContext():
            cur = 0
            cnt = len(ntc)
            for n, v in ntc.items():
                adx = self.NTC_CAL_REG_START + n
                if adx > self.NTC_CAL_REG_END: continue
                reg = TempReg('cal', adx)
                reg.set('cal', v)
                cmd = self.writeCmd(adx, reg.pack())
                self.s.write(cmd)
                #print(' '.join(f'{i:02X}' for i in cmd))
                ok, payload = self.readPacket()
                if not ok: raise BMSError()
                if payload is None: raise TimeoutError()
                if progressFunc: progressFunc(cur / cnt)
                cur += 1

    def calIdleCurrent(self):
        with self.factoryContext():
            reg = IntReg('ma', self.I_CAL_IDLE_REG, Unit.MA, 10)
            reg.set('ma', 0)
            cmd = self.writeCmd(self.I_CAL_IDLE_REG, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def calChgCurrent(self, value):
        with self.factoryContext(True):
            reg = IntReg('ma', self.I_CAL_CHG_REG, Unit.MA, 10)
            reg.set('ma', value)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def calDsgCurrent(self, value):
        with self.factoryContext(True):
            reg = IntReg('ma', self.I_CAL_DSG_REG, Unit.MA, 10)
            reg.set('ma', value)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def chgDsgEnable(self, chgEnable, dsgEnable):
        ce = 0 if chgEnable else 1
        de = 0 if dsgEnable else 1
        value = ce | (de << 1)
        with self.factoryContext():
            reg = IntReg('x', self.CHG_DSG_EN_REG, Unit.NONE, 1)
            reg.set('x', value)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def balCloseAll(self):
        self._balTestWrite(3)
    
    def balOpenOdd(self):
        self._balTestWrite(1)

    def balOpenEven(self):
        self._balTestWrite(2)

    def balExit(self):
        with self: # enter / leave factory
            pass

    def _balTestWrite(self, value):
        # Intentionally don't exit factory here
        try:
            self.open()
            self.enterFactory()
            reg = IntReg('x', self.BAL_CTRL_REG, Unit.NONE, 1)
            reg.set('x', value)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
        finally:
            self.close()

    def setPackCapRem(self, value):
        with self.factoryContext():
            reg = IntReg('mah', self.CAP_REM_REG, Unit.MAH, 10)
            reg.set('mah', value)
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

    def readIntReg(self, adx):
        with self.factoryContext():
            reg = IntReg('x', adx, Unit.NONE, 1)
            cmd = self.readCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()
            reg.unpack(payload)
            return reg.get('x')

    def writeIntReg(self, adx, value):
        with self.factoryContext():
            reg = IntReg('x', adx, Unit.NONE, 1)
            reg.set('x', int(value))
            cmd = self.writeCmd(reg.adx, reg.pack())
            self.s.write(cmd)
            ok, payload = self.readPacket()
            if not ok: raise BMSError()
            if payload is None: raise TimeoutError()

def checkRegNames():
    jbd = JBD(None)
    errors = []
    valueNamesToRegs = {}
    regNameCounts = {}
    # These have duplicate fields, but we don't care.
    ignore=BasicInfoReg,
    for reg in jbd.eeprom_regs:
        if reg.__class__ in ignore: continue
        if reg.regName not in regNameCounts:
            regNameCounts[reg.regName] = 1
        else:
            regNameCounts[reg.regName] += 1

    for regName, count in regNameCounts.items():
        if count == 1: continue
        errors.append(f'register name {regName} occurs {count} times')

    for reg in jbd.eeprom_regs:
        if reg.__class__ in ignore: continue
        valueNames = reg.valueNames
        for n in valueNames:
            if n in valueNamesToRegs:
                otherReg = valueNamesToRegs[n]
                errors.append(f'duplicate value name "{n}" in regs {reg.regName} and {otherReg.regName}')
            else:
                valueNamesToRegs[n] = reg
    return errors

# sanity check for reg setup
errors = checkRegNames()
if errors:
    for error in errors:
        print(error)
    raise RuntimeError('register errors')
del errors


class JBDUP(JBD):
    
    ADDRESS_BYTE        = 1
    REG_BYTE            = 2
    OK_BYTE             = 3
    HEADER_LENGTH       = 4


    def __init__(self, s, timeout = 1, debug = False):
        super().__init__(s,timeout, debug)

        self.basicInfoReg = BasicInfoRegUpSeries('basic_info', 0x03)
        self.serialAlwaysOpen = True

    @staticmethod
    def chksum(payload):
        return 0xFFFF - sum(payload) + 1

    def enterFactory(self):
        try:
            self.open()
            cnt = 5
            while cnt:
                cmd = self.writeCmd(self.FACTORY_MOD_REG, self.FACTORY_MOD_CMD)
                self.s.write(cmd)
                ok, x = self.readPacket()
                if ok and x is not None: # empty payload is valid
                    self.dbgPrint('enter factory: success')
                    return x
                self.dbgPrint('enter factory: no response')
                cnt -= 1
                time.sleep(.3)
            return False
        finally:
            self.close()
            
    def cmd(self, op, reg, data, address):
        payload = [reg, len(data)] + list(data)
        chksum = self.chksum([address, op] + payload)
        data = [self.START, address, op] + payload + [chksum, self.END]
        format = f'>BBB{len(payload)}BHB'
        return struct.pack(format, *data) 

    def readCmd(self, reg, data  = [], address = 0):
        return self.cmd(self.READ, reg, data, address)

    def writeCmd(self, reg, data = [], address = 0):
        return self.cmd(self.WRITE, reg, data, address)

    # zum disablen von charge Fet muss man mit FactoryMode im Register 0xE1 einen uint16 bit 0 setzen 
    # zum disablen von discharge Fet muss man mit FactoryMode im Register 0xE1 einen uint16 bit 1 setzen
 
 