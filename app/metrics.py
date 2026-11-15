"""Prometheus metrics exposed on /metrics."""

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("http_requests_total", "HTTP requests served", ["method", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
TRANSACTIONS = Counter("shopledger_transactions_total", "Ledger entries recorded", ["kind"])
OUTSTANDING = Gauge("shopledger_outstanding_rupees", "Total money customers currently owe the shop")
BUILD_INFO = Gauge("shopledger_build_info", "Running build", ["version"])
