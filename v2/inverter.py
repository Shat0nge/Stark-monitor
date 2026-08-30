import os
import time
import termios

from config import SERIAL_PORT, SERIAL_BAUD, SERIAL_TIMEOUT

PORT = SERIAL_PORT

BAUD = getattr(
    termios,
    f"B{SERIAL_BAUD}",
    termios.B2400
)

TIMEOUT = SERIAL_TIMEOUT


def setup_serial(fd):
    t = termios.tcgetattr(fd)

    t[0] = 0
    t[1] = 0
    t[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    t[3] = 0
    t[4] = BAUD
    t[5] = BAUD
    t[6][termios.VMIN] = 0
    t[6][termios.VTIME] = 20

    termios.tcsetattr(fd, termios.TCSANOW, t)


def crc16_xmodem(data):
    crc = 0

    for byte in data:
        crc ^= byte << 8

        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xffff
            else:
                crc = (crc << 1) & 0xffff

    return crc


def build_packet(command):
    cmd = command.encode("ascii")
    crc = crc16_xmodem(cmd)

    return cmd + bytes([
        (crc >> 8) & 0xff,
        crc & 0xff
    ]) + b"\r"


def query(command):
    packet = build_packet(command)

    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY)

    try:
        setup_serial(fd)
        termios.tcflush(fd, termios.TCIOFLUSH)

        os.write(fd, packet)

        result = b""
        deadline = time.time() + TIMEOUT

        while time.time() < deadline:
            chunk = os.read(fd, 4096)

            if chunk:
                result += chunk

                if b"\r" in result:
                    break

        return result

    finally:
        os.close(fd)
