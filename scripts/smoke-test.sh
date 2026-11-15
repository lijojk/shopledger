#!/usr/bin/env bash
# End-to-end check of a running ShopLedger.
# Usage: smoke-test.sh <base-url> [host-header]
#   smoke-test.sh http://127.0.0.1:8000
#   smoke-test.sh http://192.168.56.11 staging.shopledger.lab
set -euo pipefail

BASE_URL="${1:?usage: smoke-test.sh <base-url> [host-header]}"
HOST_HEADER="${2:-}"
curl_args=(--fail --silent --show-error --max-time 10)
[[ -n "${HOST_HEADER}" ]] && curl_args+=(--header "Host: ${HOST_HEADER}")

echo "1/4 waiting for the app"
for attempt in $(seq 1 30); do
  if curl "${curl_args[@]}" "${BASE_URL}/healthz" >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" -eq 30 ]]; then
    echo "app did not become healthy" >&2
    exit 1
  fi
  sleep 3
done

echo "2/4 creating a test customer"
phone="9$(date +%s | tail -c 10)"
customer=$(curl "${curl_args[@]}" -X POST "${BASE_URL}/api/customers" \
  --header 'Content-Type: application/json' \
  --data "{\"name\":\"Smoke Test\",\"phone\":\"${phone}\"}")
customer_id=$(jq -r '.id' <<<"${customer}")

echo "3/4 recording a sale and a payment"
curl "${curl_args[@]}" -X POST "${BASE_URL}/api/customers/${customer_id}/transactions" \
  --header 'Content-Type: application/json' \
  --data '{"kind":"sale","amount":"1000.50"}' >/dev/null
result=$(curl "${curl_args[@]}" -X POST "${BASE_URL}/api/customers/${customer_id}/transactions" \
  --header 'Content-Type: application/json' \
  --data '{"kind":"payment","amount":"250.25"}')

echo "4/4 checking the balance"
balance=$(jq -r '.balance' <<<"${result}")
if [[ "${balance}" != "750.25" ]]; then
  echo "expected balance 750.25, got ${balance}" >&2
  exit 1
fi
echo "smoke test passed (balance ${balance})"
