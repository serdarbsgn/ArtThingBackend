from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
app_main = FastAPI()
app_main.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.1.41:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app = APIRouter(prefix="/project")
import sqlalchemy
from sqlalchemy.pool import NullPool
from sql_dependant import env_init
sql_engine = sqlalchemy.create_engine(
                "mysql://"+env_init.MYSQL_USER+":"+env_init.MYSQL_PASSWORD+"@localhost/"+env_init.MYSQL_DB,
                isolation_level="READ UNCOMMITTED",poolclass=NullPool
                )

import views_api
import views_user_api
app_main.include_router(app)