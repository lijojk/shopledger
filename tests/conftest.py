import pytest
from sqlalchemy import create_engine

from app import create_app
from app.database import Base


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path}/test.db"
    Base.metadata.create_all(create_engine(url))
    return create_app(url).test_client()


@pytest.fixture
def customer(client):
    response = client.post("/api/customers", json={"name": "Anu", "phone": "9847000001"})
    return response.get_json()
