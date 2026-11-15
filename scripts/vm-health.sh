#!/usr/bin/env bash
# Prints a one-line health report and exits 1 if a limit is crossed.
# Run by the vm-health systemd timer every 5 minutes.
set -euo pipefail

DISK_LIMIT="${DISK_LIMIT:-85}"
MEMORY_LIMIT="${MEMORY_LIMIT:-92}"

disk_used=$(df --output=pcent / | tail -1 | tr -dc '0-9')
memory_used=$(free | awk '/^Mem:/ {printf "%d", ($2 - $7) * 100 / $2}')
load_1m=$(cut -d' ' -f1 /proc/loadavg)

echo "host=$(hostname) disk=${disk_used}% memory=${memory_used}% load=${load_1m}"

status=0
if ((disk_used >= DISK_LIMIT)); then
  echo "ALERT: disk at ${disk_used}% (limit ${DISK_LIMIT}%)" >&2
  status=1
fi
if ((memory_used >= MEMORY_LIMIT)); then
  echo "ALERT: memory at ${memory_used}% (limit ${MEMORY_LIMIT}%)" >&2
  status=1
fi
exit "${status}"
