#!/usr/bin/env bash
# Sends steady traffic so that Grafana has something to show.
# Usage: load-test.sh <base-url> [host-header] [seconds] [parallel]
set -euo pipefail

BASE_URL="${1:?usage: load-test.sh <base-url> [host-header] [seconds] [parallel]}"
HOST_HEADER="${2:-}"
DURATION="${3:-120}"
PARALLEL="${4:-4}"

header=()
[[ -n "${HOST_HEADER}" ]] && header=(--header "Host: ${HOST_HEADER}")

worker() {
  local end_time=$((SECONDS + DURATION))
  while ((SECONDS < end_time)); do
    curl --silent --output /dev/null --max-time 5 "${header[@]}" "${BASE_URL}/api/summary" || true
    curl --silent --output /dev/null --max-time 5 "${header[@]}" "${BASE_URL}/api/customers" || true
    sleep 0.1
  done
}

echo "sending traffic to ${BASE_URL} for ${DURATION}s with ${PARALLEL} workers"
for _ in $(seq 1 "${PARALLEL}"); do
  worker &
done
wait
echo "done"
