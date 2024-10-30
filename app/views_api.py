from io import BytesIO
import os
from typing import List
from fastapi.responses import FileResponse, JSONResponse
from helpers import IMAGE_DIRECTORY, PROJECT_DIR, check_file_size, get_file_md5, save_file
from sql_dependant.sql_tables import Project
from sql_dependant.sql_connection import sqlconn
from sql_dependant.sql_read import Select
from utils import check_auth
from img_tools.psd_helper import psd_check
from main import app
from fastapi import Depends, Form,  Query, UploadFile,BackgroundTasks,Request
from pydantic import BaseModel
from html import escape
from datetime import datetime



class ErrorResponse(BaseModel):
    detail: str

class MsgResponse(BaseModel):
    msg : str


@app.post('/project',
        responses={
        200: {
            "description": "Success response",
            "model": MsgResponse
        },
        401: {
            "description": "Something is wrong about the authorization token or json sent.",
            "model": ErrorResponse
        },
        400: {
            "description": "Sent file is not a psd.",
            "model": ErrorResponse
        },
        400: {
            "description": "No file received.",
            "model": ErrorResponse
        }
        })
async def check_and_save_psd_file(request:Request,background_tasks: BackgroundTasks,
                                  file: UploadFile = Depends(check_file_size),title: str = Form(...),content: str = Form(...)):
    user_info = check_auth(request)
    file_content = await file.read()
    if not file_content:
        return JSONResponse(content={"detail": "No file received."}, status_code=400)
    if not psd_check(BytesIO(file_content)):
        return JSONResponse(content={"detail": "Sent file is not a psd."}, status_code=400)
    file_hash = get_file_md5(file_content)
    filepath = os.path.join(PROJECT_DIR, "uploads/psd", file_hash+".psd")
    if not os.path.exists(filepath):
        username = "Test-Artist"
        with sqlconn() as sql:
            get_user = sql.session.execute(Select.user_username({"id":user_info["user"]})).mappings().fetchone()
            username = get_user["username"]
            project = Project(
            creator_id = user_info["user"],
            id = file_hash,
            title = escape(title),
            content=escape(content))
            sql.session.add(project)
            sql.session.commit()
        background_tasks.add_task(save_file,*(filepath,file_hash,file_content,username))
    return MsgResponse(msg="PSD saved successfully!")


class ProjectResponse(BaseModel):
    id: str
    creator: str
    creator_id:int
    title:str
    created_at:datetime
    likes:int

class ProjectsResponse(BaseModel):
    projects: List[ProjectResponse]

@app.get('/projects',
        responses={
        200: {
            "description": "Success response",
            "model": ProjectsResponse
        }
        })
async def projects(page: int = Query(0, description="Page number for pagination")):
    page_number = page
    with sqlconn() as sql:
        projects_list = sql.session.execute(Select.projects({"page":page_number})).mappings().fetchall()
    return ProjectsResponse(projects=projects_list)


class ImagesResponse(BaseModel):
    images: List[str]
    creator: str
    creator_id:int
    title: str
    content: str
    likes: int
    created_at:datetime
    user_like:str|None


@app.get('/info/{project_id}',
        responses={
        200: {
            "description": "Success response",
            "model": ImagesResponse
        }
        })
async def img(project_id:str,request:Request):
    user_project_like = None
    with sqlconn() as sql:
        info = sql.session.execute(Select.project({"project_id":project_id})).mappings().fetchone()
        try:
            user_info = check_auth(request)
            user_project_like  = sql.session.execute(Select.projectLikes_exists({"user_id":user_info["user"],"project_id":escape(project_id)})).mappings().fetchone()["l_d"]
        except:#exception means user is not logged in or doesn't have like or dislike on this project.
            pass
    images = [name for name in os.listdir(os.path.join(IMAGE_DIRECTORY,project_id)) if os.path.isfile(os.path.join(IMAGE_DIRECTORY,project_id,name))]
    images.sort()
    images.pop()#pop the last image, thumbnail.png since others will start with numbers this'll be always last.
    return ImagesResponse(images=images, **info,user_like=user_project_like)

@app.get('/image/{project_id}/{filename}',
        responses={
        200: {
            "description": "Returns the requested image file",
            "content": {"image/png": {}}
        },
        404: {
            "description": "Image not found",
            "content": {"application/json": {}}
        }
        })

async def get_image(project_id: str,filename: str):
    file_path = os.path.join(IMAGE_DIRECTORY, project_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return JSONResponse(content={"detail": "Image not found."}, status_code=404)