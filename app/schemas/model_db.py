from .database import data
from sqlalchemy import Column, String, Integer, ForeignKey, Float, DateTime, JSON
from sqlalchemy.orm import relationship

class User(data):

    __tablename__ = "User"

    id = Column(Integer, primary_key= True, index= True)
    firstname = Column(String, nullable= False)
    lastname = Column(String, nullable= False)
    username = Column(String, unique= True, nullable= False)
    email = Column(String, unique= True, nullable= False)
    password = Column(String, nullable= False)

    links = relationship("Link", back_populates= "users")

class Link(data):

    __tablename__ = "Link"

    id = Column(Integer, primary_key= True, index= True)
    link = Column(String, nullable= False)
    short_link = Column(String, nullable= False)
    qrcode = Column(String, nullable= True)
    clicks = Column(Integer, nullable= False, default= 0)
    user_id = Column(Integer, ForeignKey("User.id"))
    last_clicked = Column(DateTime, nullable= True)
    click_locations = Column(JSON, nullable= True)

    users =relationship("User", back_populates= "links")