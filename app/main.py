from fastapi import FastAPI
from .routers.user import user
from .routers.link import link 
from .routers.utils import *
from .schemas.database import engine, begin
from .schemas import model_db as model_db


app.include_router(user, prefix="/user", tags= ['User'])
app.include_router(link, prefix= "/link", tags= ['Link'])

@app.get("/")
async def landing_page():
    return "Brief is the new black, this is what inspires the team at Scissor. In today's world, it's important to keep things as short as possible, and this applies to more concepts than you may realize. From music, and speeches, to wedding receptions, brief is the new black. Scissor is a simple tool that makes URLs as short as possible. Scissor thinks it can disrupt the URL-shortening industry and give the likes of bit.ly and ow.ly a run for their money within 2 years"

model_db.data.metadata.create_all(bind = engine)