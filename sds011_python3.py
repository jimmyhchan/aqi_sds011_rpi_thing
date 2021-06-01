#!/usr/bin/env python
# coding=utf-8
# "DATASHEET": http://cl.ly/ekot
# from https://gist.github.com/kadamski/92653913a53baf9dd1a8
import serial
import struct
import sys
import time
import binascii

from typing import List, Optional

DEBUG = 1
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1

ser = serial.Serial()
ser.port = sys.argv[1]
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, data = 0, ""


def dump(d: bytes, prefix: str = '') -> None:
    print(prefix + d.hex())


def construct_command(cmd: int, data: List[int] = []) -> bytes:
    assert len(data) <= 12
    data += [0, ]*(12-len(data))
    checksum: int = (sum(data)+cmd-2) % 256
    ret: str = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    out: bytes = ret.encode('utf-8')

    if DEBUG:
        dump(out, '> ')
    return out


def process_data(d: bytes) -> str:
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(d[2:8]) % 256
    out = "PM 2.5: {} μg/m^3  PM 10: {} μg/m^3 CRC={}".format(
        pm25, pm10, "OK" if (checksum == r[2] and r[3] == 0xab) else "NOK")
    print(out)
    return out


def process_version(d: bytes) -> None:
    r = struct.unpack('<BBBHBB', d[3:])
    checksum = sum(d[2:8]) % 256
    print("Y: {}, M: {}, D: {}, ID: {}, CRC={}".format(r[0], r[1], r[2], hex(
        r[3]), "OK" if (checksum == r[4] and r[5] == 0xab) else "NOK"))


def read_response() -> bytes:
    byte = b''
    while byte != b"\xaa":
        byte = ser.read(size=1)

    d: bytes = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d


def cmd_set_mode(mode: int = MODE_QUERY) -> None:
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()


def cmd_query_data() -> Optional[str]:
    ser.write(construct_command(CMD_QUERY_DATA))
    d = read_response()
    out = None
    if d.index(b"\xc0") == 1:
        out = process_data(d)
    return out


def cmd_set_sleep(sleep: int = 1) -> None:
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()


def cmd_set_working_period(period: int) -> None:
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()


def cmd_firmware_ver() -> None:
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)


def cmd_set_id(id: int) -> None:
    id_h = (id >> 8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()


if __name__ == "__main__":
    cmd_set_sleep(0)
    cmd_set_mode(1)
    cmd_firmware_ver()
    time.sleep(3)

    cmd_query_data()
    cmd_set_mode(0)
    cmd_set_sleep()
