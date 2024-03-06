from fastapi import APIRouter, Depends,HTTPException, Body, Request, Path
from pydantic import BaseModel
from sqlalchemy import JSON
from ..schemas.database import begin
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from ..schemas.model_db import Link
from starlette import status
from .user import user_dependency
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse, RedirectResponse
from ipwhois import IPWhois
import validators
from cachetools import TTLCache, cached 
import hashlib
import qrcode
import socket

link = APIRouter()

class LinkAnalysis(BaseModel):
    link : str
    short_link : str
    custom_link : Optional[str]
    clicks : int
    last_clicked : Optional[datetime]
    click_location : list[str]

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
    prefix = "https://scissors.com/"
    short_link = f"{prefix}{short_code}"
    return short_link

#Qrcode generation
def generate_qr_code( url : str) -> bytes:
    qr = qrcode.QRCode(
        version= 1,
        error_correction = qrcode.constants.ERROR_CORRECT_L,
        box_size = 10,
        border = 4
    )

    qr.add_data(url)
    qr.make(fit = True)

    img = qr.make_image(fill_color= "black", back_color = "white")
    img_io = BytesIO()
    img.save(img_io, format = 'PNG')
    img_io.seek(0)
    return img_io.read()

#caching
cache = TTLCache(maxsize= 300, ttl= 300)

#Url shortening
@link.post("/shorten-link", status_code= status.HTTP_200_OK, response_description= {200 : {'description' : 'The user is requesting to shorten the link'}})
# @cached(cache, key = lambda user, db, url_link: user.get('user_id'))
async def shorten_link(user : user_dependency, db: db_dependency, url_link: str = Body()):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    if not validate_url(url_link):
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "The Url that you provided is invalid")

    short_code = shorten_url(url_link)
    existing_code = db.query(Link).filter(Link.short_link == short_code).first()

    if existing_code is not None:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "An error occured, please try again")

    data = Link(
        link = url_link,
        short_link = short_code,
        user_id = user.get('user_id')

    )

    db.add(data)
    db.commit()
    db.refresh(data)
    return short_code

#Get original url link from shortened link
@link.get("/shorten-link/get-original", status_code= status.HTTP_200_OK, response_description= {200 : {'description' : 'The user is requesting the original link from the shortenened version'}})
async def getting_original_link(user : user_dependency, db : db_dependency, shortened_url_link : str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    url_link = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url_link).first()

    if url_link is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link has no original link")
    
    return url_link.link


#url history
@link.get("/get-all-links", status_code= status.HTTP_200_OK , response_description= {200 : {'description' : 'The user has requested to see all links made'}})
async def link_history(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    urls = db.query(Link).filter(Link.user_id == user.get('user_id')).all()

    if not urls:
        return []

    link_data = [{'link' : urls.link, 'short_link' : urls.short_link, 'custom_link' : urls.custom_link} for urls in urls]

    return link_data

#Customizing url
@link.put("/shorten-link/customize", status_code= status.HTTP_201_CREATED, response_description= {201 : {'description' : 'The user is requesting the customize the shortenened version of the link'}})
async def customize_url(user : user_dependency, db: db_dependency, shortened_url : str, custom_url : str = Body()):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    url_link = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url).first()

    if not url_link:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found")

    existing_url = db.query(Link).filter(Link.custom_link == custom_url).first()
    if existing_url:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "Customed url already in use")
    
    if not validate_url(custom_url):
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail= "Custom url provided is not a valid url")

    url_link.custom_link = custom_url

    db.commit()
    db.refresh(url_link)

    return f"Url has been customized successfully: {url_link.custom_link}"

#qrcode generation
@link.put("/qrcode-generate", status_code= status.HTTP_201_CREATED, response_description= {201 : {'description' : 'The user is requesting the customize the to generate a qr code for the shortenened version of the link'}})
async def generate_Qr_code_image(user : user_dependency, db: db_dependency, shortened_url : str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url).first()

    if not url:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found")
    
    qr_code = generate_qr_code(url.link)

    url.qrcode = qr_code

    db.commit()
    db.refresh(url)

    return "The qrcode for this link has been generated successfully."

#get qrcode
@link.get("/qrcode", status_code= status.HTTP_200_OK, response_description= {200 :{'description' : 'The user is requesting for already generated qrcode for shortened url'}})
async def get_qr_code(user : user_dependency, db : db_dependency, shortened_url : str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthoorized user")
    
    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url).first()

    if not url:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found")

    qr_present = url.qrcode

    if qr_present is None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "There is no QR code for the shortened link!")
    
    qr_code_io = BytesIO(qr_present)
    qr_code_io.seek(0)

    return StreamingResponse(qr_code_io, media_type= "image/png")

#Ananlyzing
@link.get("/analysis/", status_code= status.HTTP_302_FOUND, response_description= {302 : {'description' : 'This endpoint is used to redirect the shortened link to menitor the clicks aspect'}})
async def redirect_to_original(db: db_dependency, shortened_url : str , request : Request):
    url = db.query(Link).filter(Link.short_link == shortened_url).first()
    if not url:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found")
    
    url.clicks += 1
    url.last_clicked = datetime.utcnow()
    client_ip = request.client.host

    if client_ip != '127.0.0.1':
        try:
            obj = IPWhois(client_ip)
            results = obj.lookup_rdap(depth=1)
            location = results['network']['remarks'][0]

            if 'click_locations' not in url:
                url.click_locations = [location]
            
            else:
                url.click_locations.append(location)

        except Exception as e:
            print(f"Failed to get user location due to: {e}")

    

    db.commit()
    db.refresh(url)
    return RedirectResponse(url= url.link)
        

@link.get("/analysis/u/", status_code= status.HTTP_200_OK, response_model= LinkAnalysis, response_description= {200 : {'description' : 'This endpoint is to monitor the analysed data from the redirect function'}})
async def analysis_for_link(db: db_dependency, user : user_dependency, shortened_url : str ):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    url = db.query(Link).filter(Link.short_link == shortened_url).filter(Link.user_id == user.get('user_id')).first()

    if not url:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found")
    
    analysis = LinkAnalysis(
        link = url.link,
        short_link= url.short_link,
        custom_link= url.custom_link,
        clicks= url.clicks,
        last_clicked= url.last_clicked,
        click_location= url.click_locations if url.click_locations else []
    )

    return analysis

#delete url
@link.delete('/delete/', status_code= status.HTTP_204_NO_CONTENT, response_description= {204 : {'description' : 'User has decided to delete a shortened link'}})
async def delete_link(user : user_dependency , db : db_dependency , shortened_url : str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url).first()

    if not url:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Shortened link not found!")
    
    db.query(Link).filter(Link.user_id == user.get('user_id')).filter(Link.short_link == shortened_url).delete()

    db.commit()

    return "Link has been deleted successfully"
