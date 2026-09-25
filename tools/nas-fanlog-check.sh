#!/usr/bin/env bash
# One-shot NAS fan-log check, run by the Windows scheduled task "NAS fan log check".
# Summarizes one full day of /var/log/minitower_fan.csv on the Pi NAS over the
# `nas` SSH alias (key auth) and writes a report to ~/Projects/nas-reports/.
# Usage: nas-fanlog-check.sh [YYYY-MM-DD]   (default: today)
DAY="${1:-$(date +%F)}"
OUT_DIR="$HOME/Projects/nas-reports"
OUT="$OUT_DIR/fanlog-$DAY.txt"
mkdir -p "$OUT_DIR"

{
  echo "NAS fan log check for $DAY  (run $(date '+%F %T'))"
  echo "=================================================="
  ssh -o BatchMode=yes -o ConnectTimeout=15 nas "DAY=$DAY bash -s" <<'REMOTE'
# If the day has already rotated past midnight, its rows are in the dated file.
F=/var/log/minitower_fan.csv
[ -f "$F.$DAY" ] && F="$F.$DAY"
echo "log file: $F"
echo
awk -F, -v day="$DAY" '
  index($1, day) != 1 { next }          # only rows from that day
  $2 !~ /^[0-9.]+$/ { next }            # skip header rows
  NF != 5 { bad++; next }               # pre-fix (shifted) rows
  { n++; t = $2 + 0; sum += t
    if (n == 1 || t < mn) mn = t
    if (t > mx) { mx = t; mxat = $1 }
    if ($3 + 0 > 0) on++
    if ($3 + 0 > mxd) mxd = $3 + 0
    if ($4 != "0x0") { thr++; flags[$5]++ } }
  END {
    if (n == 0) { print "NO clean rows found for this day"; exit }
    printf "readings:        %d (5s interval, ~%.1f h covered)\n", n, n * 5 / 3600
    if (bad) printf "skipped rows:    %d (old shifted format)\n", bad
    printf "CPU temp:        min %.1f / avg %.1f / max %.1f C (max at %s)\n", mn, sum / n, mx, mxat
    printf "fan on:          %d of %d readings (%.1f%%), max duty %.0f%%\n", on, n, 100 * on / n, mxd
    printf "throttle events: %d readings not 0x0\n", thr
    for (f in flags) printf "  %s: %d\n", f, flags[f]
  }' "$F"
echo
echo "--- current snapshot ---"
uptime
vcgencmd measure_temp; vcgencmd get_throttled
df -h /srv/dev-disk-by-uuid-8c92d026-c08b-47b6-bb6c-98b4ccf25c39 | tail -1
for s in minitower_oled minitower_fan plexmediaserver smbd docker openmediavault-engined; do
  printf "%s: %s\n" "$s" "$(systemctl is-active $s)"
done
REMOTE
  echo "ssh exit code: $?"
} > "$OUT" 2>&1

grep -v -e 'post-quantum' -e 'store now' -e 'upgraded' -e 'pq.html' "$OUT" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"
