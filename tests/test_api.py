import pytest
from sqlalchemy import create_engine, inspect

from app import create_app, migrate
from app.routes import to_paise


def test_liveness_and_readiness(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}
    assert client.get("/readyz").get_json() == {"status": "ready"}


def test_home_and_version_show_the_build(client):
    assert b"ShopLedger" in client.get("/").data
    assert client.get("/version").get_json() == {"version": "dev", "env": "local"}


def test_customer_starts_with_zero_balance(customer):
    assert customer["name"] == "Anu"
    assert customer["balance"] == "0.00"


def test_get_and_list_customers(client, customer):
    assert client.get(f"/api/customers/{customer['id']}").get_json() == customer
    assert client.get("/api/customers").get_json() == [customer]
    assert client.get("/api/customers/999").status_code == 404


def test_duplicate_phone_is_rejected(client, customer):
    response = client.post("/api/customers", json={"name": "Other", "phone": customer["phone"]})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [{}, {"name": "", "phone": "9847000002"}, {"name": "Bad", "phone": "12345"}],
)
def test_invalid_customer_is_rejected(client, payload):
    assert client.post("/api/customers", json=payload).status_code == 400


def test_sale_then_payment_changes_balance(client, customer):
    url = f"/api/customers/{customer['id']}/transactions"
    sale = client.post(url, json={"kind": "sale", "amount": "1000.50"})
    payment = client.post(url, json={"kind": "payment", "amount": 250})
    assert sale.status_code == 201
    assert sale.get_json()["balance"] == "1000.50"
    assert payment.get_json()["balance"] == "750.50"
    assert client.get("/api/summary").get_json() == {"customers": 1, "outstanding": "750.50"}


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "refund", "amount": "10"},
        {"kind": "sale", "amount": "-1"},
        {"kind": "sale", "amount": "0"},
        {"kind": "sale", "amount": "1.999"},
        {"kind": "sale", "amount": "NaN"},
        {"kind": "sale", "amount": "abc"},
    ],
)
def test_invalid_transaction_is_rejected(client, customer, payload):
    url = f"/api/customers/{customer['id']}/transactions"
    assert client.post(url, json=payload).status_code == 400


def test_transaction_for_unknown_customer(client):
    response = client.post("/api/customers/999/transactions", json={"kind": "sale", "amount": 5})
    assert response.status_code == 404


def test_money_never_uses_floats():
    assert to_paise("0.10") + to_paise("0.20") == to_paise("0.30")


def test_metrics_are_exposed(client, customer):
    client.post(
        f"/api/customers/{customer['id']}/transactions", json={"kind": "sale", "amount": 100}
    )
    body = client.get("/metrics").data.decode()
    assert "shopledger_transactions_total" in body
    assert 'route="/api/customers/<int:customer_id>/transactions"' in body
    assert "shopledger_outstanding_rupees 100.0" in body


def test_fault_injection_returns_500(client, monkeypatch):
    monkeypatch.setenv("FAULT_RATE", "1")
    assert client.get("/api/summary").status_code == 500
    assert client.get("/healthz").status_code == 200


def test_migrate_creates_tables(tmp_path, monkeypatch):
    database = tmp_path / "migrate.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    assert migrate.main() == 0
    assert "customers" in inspect(create_engine(f"sqlite:///{database}")).get_table_names()


def test_app_refuses_to_start_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


def test_database_outage_is_reported_not_hidden(tmp_path):
    client = create_app(f"sqlite:///{tmp_path}/no-tables.db").test_client()
    assert client.get("/api/summary").status_code == 503
    assert client.get("/metrics").status_code == 200
    assert client.get("/healthz").status_code == 200


def test_readiness_fails_when_database_is_unreachable(tmp_path):
    client = create_app(f"sqlite:///{tmp_path}/missing-folder/app.db").test_client()
    assert client.get("/readyz").status_code == 503
    assert client.get("/healthz").status_code == 200
