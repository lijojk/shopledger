"""HTTP routes."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from html import escape

from flask import Blueprint, Response, current_app, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from . import metrics
from .database import Customer, Transaction

bp = Blueprint("shopledger", __name__)
PHONE_PATTERN = re.compile(r"^[0-9]{10}$")
SIGNED_AMOUNT = case(
    (Transaction.kind == "sale", Transaction.amount_paise),
    else_=-Transaction.amount_paise,
)


def session():
    return current_app.config["SESSION_FACTORY"]()


def to_paise(raw: object) -> int | None:
    """Convert a rupee amount such as "199.50" to paise. Returns None if it is invalid."""
    try:
        amount = Decimal(str(raw))
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(Decimal("0.01")):
        return None
    return int(amount * 100)


def rupees(paise: int | None) -> str:
    return f"{Decimal(paise or 0) / 100:.2f}"


def balance_of(db, customer_id: int) -> int:
    query = select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)).where(
        Transaction.customer_id == customer_id
    )
    return db.scalar(query)


def customer_json(db, customer: Customer) -> dict:
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "balance": rupees(balance_of(db, customer.id)),
    }


@bp.get("/")
def home():
    version = escape(current_app.config["APP_VERSION"])
    env = escape(current_app.config["APP_ENV"])
    return (
        "<!doctype html><title>ShopLedger</title>"
        "<body style='font-family:sans-serif;max-width:40rem;margin:4rem auto'>"
        f"<h1>ShopLedger</h1><p>Environment: <b>{env}</b></p>"
        f"<p>Version: <code>{version}</code></p>"
        "<p>API: <code>/api/customers</code>, <code>/api/summary</code></p></body>"
    )


@bp.get("/healthz")
def healthz():
    """Liveness: the process can answer. Never touches the database."""
    return jsonify(status="ok")


@bp.get("/readyz")
def readyz():
    """Readiness: only take traffic when the database answers."""
    try:
        with session() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return jsonify(status="unavailable"), 503
    return jsonify(status="ready")


@bp.get("/version")
def version():
    return jsonify(version=current_app.config["APP_VERSION"], env=current_app.config["APP_ENV"])


@bp.get("/metrics")
def prometheus_metrics():
    try:
        with session() as db:
            total = db.scalar(select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)))
        metrics.OUTSTANDING.set(float(Decimal(total) / 100))
    except SQLAlchemyError:
        current_app.logger.warning("outstanding balance not refreshed")
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@bp.get("/api/customers")
def list_customers():
    with session() as db:
        customers = db.scalars(select(Customer).order_by(Customer.id).limit(200)).all()
        return jsonify([customer_json(db, customer) for customer in customers])


@bp.post("/api/customers")
def create_customer():
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    phone = str(body.get("phone", "")).strip()
    if not name or len(name) > 120:
        return jsonify(error="name is required (max 120 characters)"), 400
    if not PHONE_PATTERN.match(phone):
        return jsonify(error="phone must be 10 digits"), 400
    with session() as db:
        customer = Customer(name=name, phone=phone)
        db.add(customer)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify(error="phone already exists"), 409
        return jsonify(customer_json(db, customer)), 201


@bp.get("/api/customers/<int:customer_id>")
def get_customer(customer_id: int):
    with session() as db:
        customer = db.get(Customer, customer_id)
        if customer is None:
            return jsonify(error="customer not found"), 404
        return jsonify(customer_json(db, customer))


@bp.post("/api/customers/<int:customer_id>/transactions")
def add_transaction(customer_id: int):
    body = request.get_json(silent=True) or {}
    kind = body.get("kind")
    amount_paise = to_paise(body.get("amount"))
    if kind not in {"sale", "payment"}:
        return jsonify(error="kind must be sale or payment"), 400
    if amount_paise is None:
        return jsonify(error="amount must be positive with at most 2 decimals"), 400
    with session() as db:
        customer = db.get(Customer, customer_id)
        if customer is None:
            return jsonify(error="customer not found"), 404
        db.add(Transaction(customer_id=customer_id, kind=kind, amount_paise=amount_paise))
        db.commit()
        metrics.TRANSACTIONS.labels(kind=kind).inc()
        return jsonify(customer_json(db, customer)), 201


@bp.get("/api/summary")
def summary():
    with session() as db:
        customers = db.scalar(select(func.count(Customer.id)))
        outstanding = db.scalar(select(func.coalesce(func.sum(SIGNED_AMOUNT), 0)))
    return jsonify(customers=customers, outstanding=rupees(outstanding))
