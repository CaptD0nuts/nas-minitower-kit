#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# OLED status display for the 52Pi ABS Mini Tower NAS Kit (ZP-0128), Raspberry Pi 4.
# Shows IP address, CPU temperature, and NAS storage drive usage on the 0.96" I2C OLED (0x3C).
# Requires demo_opts.py alongside this file, and `luma.oled` + `psutil` (pip installed).

import os
import subprocess as sp
import time
from demo_opts import get_device
from luma.core.render import canvas
from PIL import ImageFont
import psutil

# Real media storage drive mount point (not the SD card root) - adjust if the drive changes.
STORAGE_PATH = "/srv/dev-disk-by-uuid-8c92d026-c08b-47b6-bb6c-98b4ccf25c39"


def bytes2human(n):
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.1f%s' % (value, s)
    return "%sB" % n


def ip_address():
    ip = sp.getoutput("hostname -I").split(' ')[0]
    return "IP: %s" % ip


def cpu_temp():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        temp_c = int(f.read().strip()) / 1000.0
    return "CPU: %.1fC" % temp_c


def disk_usage():
    # An unmounted drive leaves an empty mount folder on the SD card, and disk_usage()
    # on that folder would report the SD card's numbers as if they were the NAS drive.
    if not os.path.ismount(STORAGE_PATH):
        return "NAS: NOT MOUNTED"
    usage = psutil.disk_usage(STORAGE_PATH)
    return "NAS: %s/%s %.0f%%" % (bytes2human(usage.used), bytes2human(usage.total), usage.percent)


def stats(device):
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    font2 = ImageFont.truetype(font_path, 11)

    with canvas(device) as draw:
        draw.text((0, 2), ip_address(), font=font2, fill="white")
        draw.text((0, 24), cpu_temp(), font=font2, fill="white")
        draw.text((0, 46), disk_usage(), font=font2, fill="white")


device = get_device()

# Blank the panel overnight so a static screen doesn't burn in the OLED.
NIGHT_START, NIGHT_END = 0, 6  # local hours, 00:00-05:59
hidden = False

while True:
    night = NIGHT_START <= time.localtime().tm_hour < NIGHT_END
    if night and not hidden:
        device.hide()
        hidden = True
    elif not night:
        if hidden:
            device.show()
            hidden = False
        stats(device)
    time.sleep(5)
