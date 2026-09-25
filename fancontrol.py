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
#
# Logs temp/duty/throttle-state to LOG_PATH (CSV, daily rotation, 14 days kept) so
# cooling behavior can be reviewed after the fact - see README for how to read it.

import logging
import logging.handlers
import subprocess as sp
import time
import RPi.GPIO as GPIO

FAN_PIN = 8  # BOARD numbering = physical pin 8 = GPIO14
PWM_FREQ = 50

OFF_TEMP = 45.0
HIGH_TEMP = 65.0
LOW_DUTY = 30.0
HIGH_DUTY = 100.0

LOG_PATH = "/var/log/minitower_fan.csv"
LOG_RETAIN_DAYS = 14

# vcgencmd get_throttled bit meanings (current-state bits only; bits 16-19 are the
# "has this happened since boot" sticky versions of the same conditions).
THROTTLE_BITS = {
    0: "undervoltage",
    1: "freq_capped",
    2: "throttled",
    3: "soft_temp_limit",
}

log = logging.getLogger("fancontrol")
log.setLevel(logging.INFO)
_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_PATH, when="midnight", backupCount=LOG_RETAIN_DAYS
)
# Explicit datefmt: the default asctime ends in ",<ms>", which would split the
# timestamp into two CSV fields.
_handler.setFormatter(
    logging.Formatter("%(asctime)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
log.addHandler(_handler)


def get_cpu_temp():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read().strip()) / 1000.0


def get_throttled_flags():
    """Returns (raw_hex_string, list_of_active_current_flags)."""
    out = sp.getoutput("vcgencmd get_throttled").strip()
    # out looks like "throttled=0x50000"
    try:
        raw = out.split("=", 1)[1]
        value = int(raw, 16)
    except (IndexError, ValueError):
        return "0x0", []
    active = [name for bit, name in THROTTLE_BITS.items() if value & (1 << bit)]
    return raw, active


GPIO.setmode(GPIO.BOARD)
GPIO.setup(FAN_PIN, GPIO.OUT)
fan = GPIO.PWM(FAN_PIN, PWM_FREQ)
fan.start(0)

# CSV header, written once per service start so the log stays self-describing.
log.info("temp_c,duty_pct,throttled_raw,throttled_flags")

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

        raw, active = get_throttled_flags()
        log.info("%.1f,%.0f,%s,%s", temp, duty, raw, "|".join(active) if active else "none")

        time.sleep(5)
finally:
    fan.stop()
    GPIO.cleanup()
