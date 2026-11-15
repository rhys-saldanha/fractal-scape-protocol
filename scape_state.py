#!/usr/bin/env python3
"""Print the Fractal Scape dongle state once a second. Needs read/write access to its hidraw node."""
import glob, os, select, time


def find_hidraw():
    for uevent in glob.glob('/sys/class/hidraw/hidraw*/device/uevent'):
        if 'HID_ID=0003:000036BC:00000001' in open(uevent).read():
            return '/dev/' + uevent.split('/')[4]


def query(fd):
    try:
        while True:
            os.read(fd, 128)
    except BlockingIOError:
        pass
    os.write(fd, bytes([2, 0xF1, 0x21] + [0] * 61))
    if select.select([fd], [], [], 0.4)[0]:
        return os.read(fd, 128)[1:]  # strip report id
    return None


if __name__ == '__main__':
    fd = os.open(find_hidraw(), os.O_RDWR | os.O_NONBLOCK)
    while True:
        s = query(fd)
        if s is None:
            print('docked (no answer)')
        else:
            print(f'awake  battery={s[14]}%  arm_hall={s[13]}  muted_byte={s[4]}  bt={s[18]}  powered={s[20]}')
        time.sleep(1)
