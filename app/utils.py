from datetime import datetime
from typing import Literal
from fastapi import HTTPException
import jwt
from sql_dependant.env_init import JWT_SECRET_KEY

def decode_jwt_token(encoded_content)-> dict|Literal[False]:
    try:
        decoded_content = jwt.decode(encoded_content, JWT_SECRET_KEY, ["HS256"])
    except:
        decoded_content = False
    return decoded_content

def check_auth(request):
    if not "Authorization" in request.headers:
        raise HTTPException(status_code=401, detail="Can't get the user because token is expired or wrong.")
    test = decode_jwt_token(request.headers['Authorization'])
    if test:
        if not set(["expire_at", "user"]).issubset(set(test.keys())):
            raise HTTPException(status_code=401, detail="Can't get the user because token is expired or wrong.")
        if datetime.now() < datetime.strptime(test["expire_at"],"%Y-%m-%d %H:%M:%S.%f"):
            return test
    raise HTTPException(status_code=401, detail="Can't get the user because token is expired or wrong.")



