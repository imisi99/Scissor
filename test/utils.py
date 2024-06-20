from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from app.schemas.database import data
from app.schemas.model_db import User, Link
from app.routers.user import hash
from fastapi.testclient import TestClient
from app.main import app
import pytest

database = "sqlite:///testdb.sqlite"
engine = create_engine(database,
                       connect_args={'check_same_thread': False},
                       poolclass=StaticPool)

test_begin = sessionmaker(bind=engine, autoflush=False, autocommit=False)
data.metadata.create_all(bind=engine)


def overide_get_db():
    db = test_begin()
    try:
        yield db
    finally:
        db.close()


def overide_get_user():
    return {'username': 'Imisioluwa23', 'user_id': 1}


client = TestClient(app)


@pytest.fixture()
def test_user():
    user = User(
        id=1,
        firstname='Imisioluwa',
        lastname='Isong',
        username='Imisioluwa23',
        email='isongrichard234@gmail.com',
        password=hash.hashed("Imisioluwa234.")
    )

    db = test_begin()
    db.add(user)
    db.commit()

    yield user
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM 'User';"))
        connection.commit()


@pytest.fixture()
def test_link():
    link = Link(
        id=1,
        link='https://imisioluwa.com/aerwlsdougvs;vnsyvrhghuzbvwga',
        short_link='https://scissors.com/qwertyuiopas',
        custom_link='https://coding.com/qwertyuiopas',
        qrcode=None,
        clicks=0,
        last_clicked=None,
        click_locations=None,
        user_id=1

    )

    db = test_begin()
    db.add(link)
    db.commit()

    yield link
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM 'Link';"))
        connection.commit()
