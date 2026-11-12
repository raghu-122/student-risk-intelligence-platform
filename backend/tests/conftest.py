"""
Backend test suite — uses SQLite in-memory for isolation.
Tests risk engine, anomaly detection, API endpoints, lifecycle rules.
"""
import pytest
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-purposes-32chars"

# Override database for tests
import app.db.database as _db_module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = "sqlite:///./test_sqlite.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

_db_module.engine = test_engine
_db_module.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables in SQLite test DB."""
    from app.db.database import Base
    import app.models  # noqa: register all models
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    import time
    time.sleep(0.1)
    if os.path.exists("test_sqlite.db"):
        try:
            os.remove("test_sqlite.db")
        except PermissionError:
            pass  # File still in use on Windows; leave cleanup to OS


@pytest.fixture
def db():
    """Provide a transactional test session that rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI test client with overridden DB dependency."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.database import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client, db):
    """Create admin user and return auth headers."""
    from app.models.user import User
    from app.core.security import hash_password
    if not db.query(User).filter(User.username == "testadmin").first():
        u = User(user_id="USR-TEST-001", username="testadmin",
                 email="testadmin@test.com",
                 hashed_password=hash_password("testpass123"),
                 role="PLATFORM_ADMINISTRATOR", is_active=True)
        db.add(u); db.commit()
    resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

