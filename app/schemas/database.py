from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

database_url = 'postgresql://ivgzbexn:QDKx7C6ImQ7YAvS7f6XP1KivA-NgUNui@trumpet.db.elephantsql.com/ivgzbexn'
engine = create_engine(database_url)
begin = sessionmaker(bind= engine, autoflush= False, autocommit = False)
data = declarative_base()