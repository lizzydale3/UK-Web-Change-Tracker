import os
import pytest
from mongomock import MongoClient as MockClient

from app import create_app
import app.db.mongo as mongo_mod
import app.config as cfg
import requests


class _DummyResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._payload


@pytest.fixture(scope="session")
def mock_db():
    client = MockClient()
    return client["internet_tracker_test"]


@pytest.fixture(autouse=True)
def _patch_db(monkeypatch, mock_db):
    monkeypatch.setattr(mongo_mod, "get_db", lambda: mock_db, raising=True)
    monkeypatch.setattr(mongo_mod, "get_collection", lambda name: mock_db[name], raising=True)
    yield
    for name in list(mock_db.list_collection_names()):
        mock_db[name].delete_many({})


@pytest.fixture(autouse=True)
def _patch_cfg(monkeypatch):
    monkeypatch.setattr(cfg, "FLASK_ENV", "testing", raising=False)
    monkeypatch.setattr(cfg, "MONGO_DB", "internet_tracker_test", raising=False)
    monkeypatch.setattr(cfg, "CLOUDFLARE_API_TOKEN", "test-token", raising=False)
    monkeypatch.setattr(cfg, "CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4", raising=False)
    yield


@pytest.fixture
def app_client():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app()
    with app.test_client() as c:
        yield c


@pytest.fixture
def fake_requests(monkeypatch):
    calls = []

    def install(mapper):
        def _get(url, headers=None, params=None, timeout=None):
            calls.append({"url": url, "headers": headers, "params": params})
            if callable(mapper):
                payload, status = mapper(url, headers, params)
            else:
                payload, status = mapper.get(url, ({}, 200))
            return _DummyResp(status_code=status, payload=payload)

        monkeypatch.setattr("requests.get", _get, raising=True)
        return calls

    return install
