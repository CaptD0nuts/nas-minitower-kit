#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Temperature-based PWM fan control for the 52Pi ABS Mini Tower NAS Kit (ZP-0128),
# Raspberry Pi 4. Fan control wire is GPIO14 / physical pin 8 (confirmed by direct
# hardware test - forcing 100% duty audibly spun the fan up).
#
# GPIO14 doubles as the Pi's default serial-console TX pin (console=serial0 in
# cmdline.txt) - using it here takes over that pin while this service runs. Harmless
# on a headless NAS with no serial cable in use; stop this service first if serial
# console access is ever needed.
#
# If a different unit/revision needs a different pin, just change FAN_PIN below and
# restart the systemd service - nothing else needs to change.

import time
import RPi.GPIO as GPIO

FAN_PIN = 8  # BOARD numbering = physical pin 8 = GPIO14
PWM_FREQ = 50

OFF_TEMP = 45.0
HIGH_TEMP = 65.0
LOW_DUTY = 30.0
HIGH_DUTY = 100.0


def get_cpu_temp():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read().strip()) / 1000.0


GPIO.setmode(GPIO.BOARD)
GPIO.setup(FAN_PIN, GPIO.OUT)
fan = GPIO.PWM(FAN_PIN, PWM_FREQ)
fan.start(0)

try:
    while True:
        temp = get_cpu_temp()
        if temp < OFF_TEMP:
            duty = 0.0
        elif temp >= HIGH_TEMP:
            duty = HIGH_DUTY
        else:
            span = HIGH_TEMP - OFF_TEMP
            duty = LOW_DUTY + (HIGH_DUTY - LOW_DUTY) * (temp - OFF_TEMP) / span
        fan.ChangeDutyCycle(duty)
        time.sleep(5)
finally:
    fan.stop()
    GPIO.cleanup()
