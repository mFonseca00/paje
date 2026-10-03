import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.config import settings


from backend.armazenamento.modelos import Base


TEST_DB_URL = (
    f"postgresql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/paje_test"
)

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(test_engine) -> Session:
    conn = test_engine.connect()
    transaction = conn.begin()
    sess = Session(bind=conn)
    yield sess
    sess.close()
    transaction.rollback()
    conn.close()
