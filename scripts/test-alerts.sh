#!/usr/bin/env bash
# Unit-tests the alert rules with promtool, inside a container.
set -euo pipefail

python3 - <<'PY'
import yaml

with open("monitoring/alerts.yaml") as source:
    rule = yaml.safe_load(source)
with open("/tmp/shopledger-rules.yaml", "w") as target:
    yaml.safe_dump(rule["spec"], target, sort_keys=False)
PY

docker run --rm --entrypoint promtool \
  --volume /tmp/shopledger-rules.yaml:/tmp/shopledger-rules.yaml:ro \
  --volume "${PWD}/monitoring:/monitoring:ro" \
  prom/prometheus:v3.5.0 test rules /monitoring/tests/alerts_test.yaml
