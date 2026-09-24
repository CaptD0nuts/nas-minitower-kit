# nas-minitower-kit

OLED status screen + temperature-based fan control for a **52Pi ABS Mini Tower NAS Kit (SKU ZP-0128)** on a Raspberry Pi 4 running OpenMediaVault + Plex on Debian 11 (Bullseye).

The vendor's official installer (`geeekpi/absminitowerkit`, `install_bookworm.sh`) was intentionally **not** used as-is: it's written for Raspberry Pi OS Bookworm (wrong `config.txt` path, wrong default `pi` user on this box), and it also silently rewrites `/etc/resolv.conf` to hardcoded DNS servers (including a Chinese DNS host) as an undisclosed side effect. Everything here is a minimal, scoped-down replacement.

## What's here

- `sysinfo.py` + `demo_opts.py` — drives the 0.96" I2C OLED (address `0x3C`). Shows IP address, CPU temperature, and the actual NAS storage drive's usage (not the SD card).
- `fancontrol.py` — PWM fan control on `GPIO14` (physical pin 8), confirmed by direct hardware test. Off below 45°C, linear ramp 30-100% duty between 45-65°C, full above 65°C. Logs every reading (temp, duty %, and the Pi's own `vcgencmd get_throttled` state) to `/var/log/minitower_fan.csv`, daily rotation, 14 days kept.
- `systemd/minitower_oled.service`, `systemd/minitower_fan.service` — systemd units for both.

## Deploy (on the Pi)

```sh
sudo raspi-config nonint do_i2c 0   # enable I2C
sudo -H pip3 install luma.oled psutil RPi.GPIO

sudo mkdir -p /usr/local/minitower
sudo cp demo_opts.py sysinfo.py fancontrol.py /usr/local/minitower/

sudo cp systemd/minitower_oled.service systemd/minitower_fan.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minitower_oled.service minitower_fan.service
```

Edit `STORAGE_PATH` in `sysinfo.py` if the NAS drive's UUID-based mount path ever changes.

## Checking cooling performance

```sh
tail -f /var/log/minitower_fan.csv
```

Each line is `timestamp,temp_c,duty_pct,throttled_raw,throttled_flags`. `throttled_flags` will read `none` normally; if it ever shows `undervoltage`, `freq_capped`, `throttled`, or `soft_temp_limit`, the Pi's own firmware has detected a real problem at that moment (not just our own temperature guess) — worth investigating airflow/dust/thermal paste if that starts showing up during normal load.

To eyeball whether the fan ramps sensibly with load, watch the log while doing something CPU-heavy (e.g. a Plex transcode) and confirm `duty_pct` climbs as `temp_c` rises, and drops back down afterward.

## Notes

- Installed via `pip`, not `apt`, deliberately — keeps this isolated from OMV's own apt/Python-managed packages.
- `GPIO14` doubles as the Pi's default serial-console TX pin. Using it for the fan takes over that pin while the service runs — harmless on a headless NAS with no serial cable in use, but stop `minitower_fan.service` first if serial console access is ever needed.
- If a different unit/revision needs a different fan pin, change `FAN_PIN` in `fancontrol.py` and `systemctl restart minitower_fan.service` — nothing else needs to change.
- This box's `security.debian.org` bullseye-security repo has been intermittently 404ing on specific package files even after `apt update` (hit this installing `git` and `python3-setuptools`). If that recurs, either temporarily disable `/etc/apt/sources.list.d/openmediavault-os-security.list` for the affected install, or bootstrap pip via `https://bootstrap.pypa.io/pip/3.9/get-pip.py` instead of apt.
