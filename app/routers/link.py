from fastapi import Depends, HTTPException, Body, Request
from pydantic import BaseModel
from sqlalchemy import or_
from ..schemas.database import begin
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from ..schemas.model_db import Link
from starlette import status
from .user import get_user
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse, RedirectResponse
from ipwhois import IPWhois
from .utils import *
import validators
from functools import lru_cache
from slowapi import _rate_limit_exceeded_handler, Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import hashlib
from urllib.parse import urlunparse, urlparse
import qrcode

limiter = Limiter(key_func=get_remote_address)


class LinkAnalysis(BaseModel):
    link: str
    short_link: str
    custom_link: Optional[str]
    clicks: int
    last_clicked: Optional[datetime]
    click_location: list[str]


'''
Database initialization
'''


def get_db():
    db = begin()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[str, Depends(get_user)]

'''
Url validation and shortening
'''


def validate_url(url):
    return validators.url(url)


def shorten_url(url):
    hash_object = hashlib.sha256(url.encode())
    short_code = hash_object.hexdigest()[:12]
    prefix = "https://scissors.com/"
    short_link = f"{prefix}{short_code}"
    return short_link


'''
Qrcode generation
'''


def generate_qr_code(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )

    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    return img_io.read()


'''
caching

rate limiting
'''

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

'''
This route is to create a shortened link but it would fail to do so it the provided url is not valid
validity of a url entails that the url must be secured {https://} it must have a domain name (scissor.com)
'''


# Caching the response in shortening
@lru_cache(maxsize=200)
def shorten_link_cache(user_id: str, url_link: str, db: Session):
    existing_link = db.query(Link).filter(Link.user_id == user_id).filter(Link.link == url_link).first()
    if existing_link:
        return f'Link already exists: {existing_link.short_link}'
    if not validate_url(url_link):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The Url that you provided is invalid")

    short_code = shorten_url(url_link)
    existing_code = db.query(Link).filter(Link.short_link == short_code).first()

    if existing_code is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An error occurred, please try again")

    data = Link(
        link=url_link,
        short_link=short_code,
        user_id=user_id

    )

    db.add(data)
    db.commit()
    db.refresh(data)

    return short_code


@link.post("/shorten-link", status_code=status.HTTP_201_CREATED,
           response_description={201: {'description': 'The user is requesting to shorten the link'}})
@limiter.limit("5/hour")
async def shorten_link(request: Request, user: user_dependency, db: db_dependency, url_link: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    response = shorten_link_cache((user.get('user_id')), url_link, db)
    return {"Short Code": response}


# Get original url link from shortened link
@lru_cache(maxsize=128)
def get_original_url(user_id: str, shortened_url_link: str, db: Session):
    url_link = db.query(Link).filter(
        or_(Link.custom_link == shortened_url_link, Link.short_link == shortened_url_link)).filter(
        Link.user_id == user_id).first()

    if url_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="The link that you provided has no original link linked to it")

    return url_link.link


@link.get("/shorten-link/get-original", status_code=status.HTTP_200_OK, response_description={
    200: {'description': 'The user is requesting the original link from the shortened version'}})
async def getting_original_link(user: user_dependency, db: db_dependency, shortened_url_link: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    original_link = get_original_url(user.get("user_id"), shortened_url_link, db)
    return {'original_link': original_link}


# Url history
@link.get("/get-all-links", status_code=status.HTTP_200_OK,
          response_description={200: {'description': 'The user has requested to see all links made'}})
async def link_history(user: user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    urls = db.query(Link).filter(Link.user_id == user.get('user_id')).all()

    if not urls:
        return []

    link_data = [{'link': urls.link, 'short_link': urls.short_link, 'custom_link': urls.custom_link} for urls in urls]

    return link_data


'''
This route is to customize the url provided but only the domain name can be changed
The customized url can also be used to perform the functionality of the original shortened url generated 
'''


@link.put("/shorten-link/customize", status_code=status.HTTP_201_CREATED, response_description={
    201: {'description': 'The user is requesting the customize the shortened version of the link'}})
async def customize_url(user: user_dependency, db: db_dependency, shortened_url: str, domain_name: str = Body()):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    url_link = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(
        Link.short_link == shortened_url).first()

    if not url_link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link")

    parsed_url = urlparse(shortened_url)

    custom_url = urlunparse(
        (parsed_url.scheme, domain_name, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))

    existing_url = db.query(Link).filter(Link.custom_link == custom_url).first()
    if existing_url:
        raise HTTPException(status_code=status.HTTP_226_IM_USED, detail="Customized url already in use")

    if not validate_url(custom_url):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Custom url provided is not a valid url")

    url_link.custom_link = custom_url

    db.commit()
    db.refresh(url_link)

    return f"Url has been customized successfully: {url_link.custom_link}"


'''
This route is to generate the QR code for a particular link but not to view it
To do so you would have to use the route below
'''


@link.put("/qrcode-generate", status_code=status.HTTP_201_CREATED, response_description={201: {
    'description': 'The user is requesting the customize the to generate a qr code for the shortened '
                   'version of the link'}})
@limiter.limit("5/hour")
async def generate_Qr_code_image(request: Request, user: user_dependency, db: db_dependency, shortened_url: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(
        or_(Link.custom_link == shortened_url, Link.short_link == shortened_url)).first()

    if url.qrcode is not None:
        return 'There is a QR code already generated for this link'

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link!")

    qr_code = generate_qr_code(url.link)

    url.qrcode = qr_code

    db.commit()
    db.refresh(url)

    return "The Qrcode for this link has been generated successfully."


'''
This route is used to get or view the qrcode that should have been generated using the route above

'''


@link.get("/qrcode", status_code=status.HTTP_200_OK, response_description={
    200: {'description': 'The user is requesting for already generated qrcode for shortened url'}})
async def get_qr_code(user: user_dependency, db: db_dependency, shortened_url: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(
        or_(Link.custom_link == shortened_url, Link.short_link == shortened_url)).first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link!")

    qr_present = url.qrcode

    if qr_present is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="There is no QR code for the shortened link!")

    qr_code_io = BytesIO(qr_present)
    qr_code_io.seek(0)

    return StreamingResponse(qr_code_io, media_type="image/png")


'''
This route is to analysis the link and the method to do so
It defines the method and also a way to view the analysis
'''


@link.get("/analysis/", status_code=status.HTTP_302_FOUND, response_description={
    302: {'description': 'This endpoint is used to redirect the shortened link to monitor the clicks aspect'}})
@limiter.limit("5/minute")
async def redirect_to_original(db: db_dependency, shortened_url: str, request: Request):
    url = db.query(Link).filter(or_(Link.short_link == shortened_url, Link.custom_link == shortened_url)).first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link")

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
    return RedirectResponse(url=url.link)


@link.get("/analysis/u/", status_code=status.HTTP_200_OK, response_model=LinkAnalysis, response_description={
    200: {'description': 'This endpoint is to monitor the analysed data from the redirect function'}})
async def analysis_for_link(db: db_dependency, user: user_dependency, shortened_url: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")
    url = db.query(Link).filter(or_(Link.custom_link == shortened_url, Link.short_link == shortened_url)).filter(
        Link.user_id == user.get('user_id')).first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link")

    analysis = LinkAnalysis(
        link=url.link,
        short_link=url.short_link,
        custom_link=url.custom_link,
        clicks=url.clicks,
        last_clicked=url.last_clicked,
        click_location=url.click_locations if url.click_locations else []
    )

    return analysis


'''
A route for the user to delete a link
'''


@link.delete('/delete/', status_code=status.HTTP_204_NO_CONTENT,
             response_description={204: {'description': 'User has decided to delete a shortened link'}})
async def delete_link(user: user_dependency, db: db_dependency, shortened_url: str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized user")

    url = db.query(Link).filter(Link.user_id == user.get('user_id')).filter(
        or_(Link.custom_link == shortened_url, Link.short_link == shortened_url)).first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid link!")

    db.query(Link).filter(Link.user_id == user.get('user_id')).filter(
        or_(Link.custom_link == shortened_url, Link.short_link == shortened_url)).delete()

    db.commit()

    return "Link has been deleted successfully"
