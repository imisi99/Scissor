from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

database_url = 'postgresql://postgres:Imisioluwa234.@localhost/Scissors'
engine = create_engine(database_url)
begin = sessionmaker(bind= engine, autoflush= False, autocommit = False)
data = declarative_base()