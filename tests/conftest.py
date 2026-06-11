import os
import pytest
from app import create_app
from app.extensions import db

@pytest.fixture(scope="session")
def app():
    """Create a Flask app context for testing."""
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    
    app = create_app("testing")
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    session = db.create_scoped_session(options={"bind": connection, "binds": {}})
    db.session = session
    
    yield session
    
    transaction.rollback()
    connection.close()
    session.remove()
