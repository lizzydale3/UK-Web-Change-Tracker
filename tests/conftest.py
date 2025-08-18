import os
import pytest

# Keep DB out of unit tests unless explicitly needed
os.environ.setdefault("MONGODB_URI", "")
os.environ.setdefault("MONGO_DB", "internet_tracker_test")
os.environ.setdefault("FLASK_ENV", "testing")

from app import create_app  # noqa: E402

@pytest.fixture(scope="session")
def app():
    try:
        flask_app = create_app(testing=True)  # if your factory accepts it
    except TypeError:
        flask_app = create_app()
        flask_app.config.update(TESTING=True)
    return flask_app

@pytest.fixture()
def app_client(app):
    return app.test_client()
