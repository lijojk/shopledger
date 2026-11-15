"""ShopLedger: a small customer-balance API for a retail shop."""

from __future__ import annotations

import logging
import os
import random
import time

from flask import Flask, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from . import metrics
from .database import build_session_factory
from .routes import bp

UNTRACKED_PATHS = {"/metrics", "/healthz", "/readyz"}


def create_app(database_url: str | None = None) -> Flask:
    """Application factory used by gunicorn and by the tests."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = Flask(__name__)
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")

    app.config["SESSION_FACTORY"] = build_session_factory(url)
    app.config["APP_ENV"] = os.environ.get("APP_ENV", "local")
    app.config["APP_VERSION"] = os.environ.get("APP_VERSION", "dev")
    metrics.BUILD_INFO.labels(version=app.config["APP_VERSION"]).set(1)
    app.register_blueprint(bp)

    @app.before_request
    def start_timer_and_maybe_fail():
        g.started_at = time.perf_counter()
        # FAULT_RATE lets the failure drills raise real 5xx errors on purpose.
        fault_rate = float(os.environ.get("FAULT_RATE", "0"))
        if request.path.startswith("/api") and random.random() < fault_rate:  # noqa: S311
            return jsonify(error="injected fault"), 500
        return None

    @app.after_request
    def record_metrics(response):
        if request.path not in UNTRACKED_PATHS:
            # The route template keeps label cardinality low: /api/customers/<int:customer_id>
            route = request.url_rule.rule if request.url_rule else "unmatched"
            metrics.REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            metrics.LATENCY.labels(request.method, route).observe(
                time.perf_counter() - g.started_at
            )
        return response

    @app.errorhandler(SQLAlchemyError)
    def database_unavailable(error):
        app.logger.error("database error: %s", error)
        return jsonify(error="database unavailable"), 503

    return app
