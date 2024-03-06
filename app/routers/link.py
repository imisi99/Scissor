from fastapi import APIRouter, Depends,HTTPException
from pydantic import BaseModel
from ..schemas.database import begin
from typing import Annotated
from sqlalchemy.orm import Session
from ..schemas.model_db import Link
from starlette import status
from .user import user_dependency
import validators
import hashlib


link = APIRouter()
#Database initialization
def get_db():
    db = begin()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

#Url validation and shortening
def validate_url(url):
    return validators.url(url)

def shorten_url(url):
    hash_object = hashlib.sha256(url.encode())
    short_code = hash_object.hexdigest()[:12]
    return short_code

#Url shortening
@link.post("/shorten-link", status_code= status.HTTP_200_OK, response_description= {200 : {'description' : 'The user is requesting to shorten the link'}})
async def shorten_link(user : user_dependency, db: db_dependency, url_link: str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    if not validate_url(url_link):
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "The Url that you provided is invalid")

    short_code = shorten_url(url_link)

    return short_code

@link.get("/shorten-link/original-link",  status_code= status.HTTP_200_OK, response_description= {200 : {'description' : 'The user is requesting the original link from the shortenened version'}})
async def getting_original_link(user : user_dependency, db : db_dependency, shortened_url_link : str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    url = db.query(Link).filter(Link.short_link == shortened_url_link)

    if url is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link has no original link")
    
    
#Customizing url
#qrcode generation
#Ananlyzing
#url history
#delete url
