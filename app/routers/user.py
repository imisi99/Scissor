from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, validator
from starlette import status
from ..schemas.database import begin
from sqlalchemy.orm import Session
from .utils import *
from ..schemas.model_db import User, Link
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import re


#Database
def get_db():
    db =begin()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

#hashing method
hash = CryptContext(schemes=['bcrypt'])

#User authentication and authorization
def authorization(username : str, password : str , db):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
    password = hash.verify(password, user.password)
    if not password:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
    
    return user 

Secret = "6217bb23e89b7030aa36362a7111c9f2efc620c1efeb8f97dda9b5c125fb2f934359a808cb55fc98a7a370742abcaaacc59768a9df41b2fddc1b3dffdbd5361f"
Algorithm = "HS256"

def authentication(username : str, user_id : int, timedelta):
    encode = {'sub' : username, 'id' : user_id}
    expired = datetime.utcnow() + timedelta
    encode.update({'exp' : expired})
    return jwt.encode(encode, Secret, algorithm= Algorithm)

bearer = OAuth2PasswordBearer(tokenUrl= "user/login")
async def get_user(token : Annotated[str, Depends(bearer)]):
    try:
        payload = jwt.decode(token, Secret, algorithms= [Algorithm])
        username : str = payload.get('sub')
        user_id : int = payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
        
        return {
            'username' : username,
            'user_id' : user_id
        }
    
    except JWTError as e :
        print(f'JWTError occured as : {e}')
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "User timed out due to inactivity, login to continue")
    
user_dependency = Annotated[str, Depends(get_user)]
class Signup(BaseModel):
    firstname : Annotated[str, Field(min_length=3)]
    lastname : Annotated[str, Field(min_length= 3)]
    username : str
    email : EmailStr
    password : str

    @validator('password')
    def check_password(cls,value):
        if len(value) < 8 :
            raise ValueError("Password must contain at least 8 characters!")
        if not any (char.isupper() for char in value):
            raise ValueError("Password must contain at least one upper character!")
        if not re.search(r'[!@#$%^&*()<>?:,.;{}|]', value):
            raise ValueError("Password must contain at least one special character!")
        
        return value
    
    @validator('username')
    def check_username(cls,value):
        if len(value) < 8 :
            raise ValueError("Usernmae must be more than 8 characters long! ")
        if len(value) > 15 :
            raise ValueError("Username must be less than 15 characters long!")
        
        return value.replace(" ", "")
    class Config():
        json_schema_extra = {
            'example' : {
                'firstname' : 'Firstname',
                'lastname' : "Lastname",
                'username' : "Username",
                'email' : 'email@gmail.com',
                'password' : "Password"
            }
        }
class GetUserDetails(BaseModel):
    firstname : str
    lastname : str
    username : str
    email : str

class UpdateDetails(BaseModel):
    firstname : Annotated[str, Field(min_length= 3)]
    lastname : Annotated[str, Field(min_length= 3)]
    email : EmailStr
    username : str

    @validator('username')
    def check_username(cls,value):
        if len(value) < 8 :
            raise ValueError("Usernmae must be more than 8 characters long! ")
        if len(value) > 15 :
            raise ValueError("Username must be less than 15 characters long!")
        
        return value.replace(" ", "")
    
    class Config():
        json_schema_extra = {
            'example' : {
                'firstname' : 'Firstname',
                'lastname' : "Lastname",
                'username' : "Username",
                'email' : 'email@gmail.com'
            }
        }

class Token(BaseModel):
    access_token : str
    token_type : str

class ForgotPassword(BaseModel):
    username : Annotated[str, Field()]
    email : Annotated[str, Field()]
    new_password : Annotated[str, Field()]
    confirm_password : Annotated[str, Field()]

    @validator('new_password')
    def check_password(cls, value):
        if len(value) < 8 :
            raise ValueError("Password must contain at least 8 characters!")
        if not any (char.isupper() for char in value):
            raise ValueError("Password must contain at least one upper character!")
        if not re.search(r'[!@#$%^&*()<>?:,.;{}|]', value):
            raise ValueError("Password must contain at least one special character!")
        
        return value
    
    class Config():
        json_schema_extra = {
            'example' : {
                'username' : 'username',
                'email' : "email",
                'new_password' : "password",
                'confirm_password' : 'password'
            }
        }
    

#user signup 
@user.post("/signup", status_code= status.HTTP_201_CREATED , response_description= {201 : {'description' : 'User has signed up successfully.'}})
async def user_signup(form : Signup, db : db_dependency):
    existing_username = db.query(User).filter(form.username == User.username).first()
    existing_email = db.query(User).filter(form.email == User.email).first()

    if existing_email and existing_username is not None:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "email and username already in use!")
    
    if existing_username:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "username already in use!")
    
    if existing_email:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "email is already in use!")
    
    user = User(
        firstname = form.firstname,
        lastname = form.lastname,
        username = form.username,
        email = form.email,
        password = hash.hash(form.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return "User has signed up successfully"

#User login 
@user.post("/login", response_model= Token, status_code= status.HTTP_202_ACCEPTED , response_description= {202 : {'description' : 'User has logged in successfully.'}})
async def log_in(form : Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authorization(form.username, form.password, db)

    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
    
    token = authentication(user.username, user.id, timedelta(minutes= 15))

    if not token:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "Error while trying to log you in please try again later!")
    
    return {
        "access_token" : token,
        "token_type" : "bearer"
    }

#get user details 
@user.get("/user-details", status_code= status.HTTP_200_OK, response_description= {200 : {'description' : 'User has requested for the details.'}})
async def get_current_user(user : user_dependency, db: db_dependency):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
    
    details = db.query(User).filter(User.id == user.get('user_id')).first()
    if not details:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "An error occured while trying to fetch details, please try again later")
    data = GetUserDetails(
        firstname= details.firstname,
        lastname= details.lastname,
        username= details.username,
        email= details.email
    )

    return data

#user update details
@user.put("/user-details/update", status_code= status.HTTP_202_ACCEPTED, response_description= {202 :{'description': 'User has successfully change the details'}})
async def update_details(user : user_dependency, db : db_dependency, form : UpdateDetails):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")

    details = db.query(User).filter(User.id == user.get('user_id')).first()

    existing_email = db.query(User).filter(User.email == form.email).first()
    existing_username = db.query(User).filter(User.username == form.username).first()

    if existing_email is not None and existing_email.email != details.email:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "email is already in use")
    
    if existing_username is not None and existing_username.username != details.username:
        raise HTTPException(status_code= status.HTTP_226_IM_USED, detail= "username is already in use")
    
   
    if not details:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "User not found, please login and try again later!")
    
    details.firstname = form.firstname
    details.lastname = form.lastname
    details.username = form.username
    details.email = form.email

    db.add(details)
    db.commit()
    db.refresh(details)

    return "User details have been updated successfully."

#user forgot password
@user.put("/forgot-password/recovery", status_code= status.HTTP_202_ACCEPTED, response_description= {202 :{'description': 'User has successfully verified account and changed password'}})
async def forgot_password(form : ForgotPassword, db: db_dependency):
    user = db.query(User).filter(User.email == form.email).filter(User.username == form.username).first()

    if not user:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail= "Invalid credentials")
    
    if form.new_password != form.confirm_password:
        raise HTTPException(status_code= status.HTTP_406_NOT_ACCEPTABLE, detail= "Passwords does not match!")
    
    user.password = hash.hash(form.new_password)

    db.add(user)
    db.commit()
    db.refresh(user)

#user change password
@user.put("/change-password/", status_code= status.HTTP_202_ACCEPTED, response_description= {202 :{'description': 'User has successfully changed password'}})
async def change_password(user : user_dependency, db : db_dependency, current_password : str, new_password: str):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user")
    
    data = db.query(User).filter(User.id == user.get('user_id')).first()
    if not data:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail="User not found, please login and try again")
    
    password = hash.verify(current_password, data.password)

    if not password:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Invalid password!")
    
    if len(new_password) < 8:
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail= "Password must be at least 8 characters long!")
    if not any(char.isupper() for char in new_password):
        raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail= "Password must contain at least one uppercase character")
    if not re.search(r'[!@#$%^&*()<>?:,.;{}|]', new_password):
            raise HTTPException(status_code= status.HTTP_422_UNPROCESSABLE_ENTITY, detail= "Password must contain at least one special character!")

    data.password = hash.hash(new_password)

    db.add(data)
    db.commit()
    db.refresh(data)

    return "User password has been updated successfully."

#user delete
@user.delete("/user/delete-user", status_code= status.HTTP_204_NO_CONTENT, response_description= {204 : {'description' : 'User has decided to delete his account'}})
async def delete_user(user: user_dependency, db : db_dependency):
    if not user:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail= "Unauthorized user!")
    
    user_delete = db.query(User).filter(User.id == user.get('user_id')).first()
    links_delete = db.query(Link).filter(Link.user_id == user.get('user_id')).delete()

    if not user_delete:
        raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail= "We encountered an error while trying to delete your data, please try again later.")
    
    if not links_delete:
        pass

    db.delete(user_delete)
    db.commit()

    return "User data has been deleted successfully."