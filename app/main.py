from fastapi import FastAPI
from .routers.user import user
from .routers.link import link 
from .routers.utils import *
from .schemas.database import engine, begin
from .schemas import model_db as model_db


app.include_router(user, prefix="/user", tags= ['User'])
app.include_router(link, prefix= "/link", tags= ['Link'])

app.get("/")
async def landing_page():
    return ""

model_db.data.metadata.create_all(bind = engine)