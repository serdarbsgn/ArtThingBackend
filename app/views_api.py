from io import BytesIO
import json
import os
from typing import List
from fastapi.responses import FileResponse, JSONResponse
from .helpers import IMAGE_DIRECTORY, PROJECT_DIR, check_file_size, get_file_md5, limit_line_breaks, save_file
from .sql_dependant.sql_tables import Project
from .sql_dependant.sql_connection import sqlconn
from .sql_dependant.sql_read import Select
from .utils import check_auth
from .img_tools.psd_helper import psd_check
from .main import app
from fastapi import Depends, Form,  Query, UploadFile,BackgroundTasks,Request
from pydantic import BaseModel
from html import escape
from datetime import datetime, timedelta



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
            content=limit_line_breaks(escape(content),20))
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
    variations:int
    user_like:str|None


@app.get('/project/{project_id}',
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

    image_dir = os.path.join(IMAGE_DIRECTORY, project_id)
    cache_path = os.path.join(image_dir,"cache.json")
    is_cache_stale = True
    data = {}
    if os.path.exists(cache_path):
        with open(cache_path, "r") as cache_file:
            data = json.load(cache_file)
        cache_timestamp = datetime.fromisoformat(data.get("timestamp", "1970-01-01T00:00:00"))
        if datetime.now() - cache_timestamp < timedelta(hours=24):
            is_cache_stale = False

    if is_cache_stale:
        all_images = [name for name in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, name)) and name.endswith(".png") or name.endswith(".webp")]
        original_images = [name for name in all_images if name.count('_') == 2 and name.endswith(".png")]
        original_images.sort()
        if len(original_images) == 1:
            variations = 0
        else:
            variations_png = sum(1 for name in all_images if name.startswith("1_") and name.count('_') == 3 and name.endswith(".png"))
            variations_webp = sum(1 for name in all_images if name.startswith("1_") and name.count('_') == 3 and name.endswith(".webp"))
            variations = max(variations_png,variations_webp)
        data = {
                "timestamp": datetime.now().isoformat(),
                "images": original_images,
                "variations": variations,
            }
        with open(cache_path, "w") as cache_file:
            json.dump(data, cache_file)

    return ImagesResponse(images=data["images"], variations=data["variations"], **info, user_like=user_project_like)

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
    base_name, ext = os.path.splitext(file_path)
    fallback_ext = ".webp" if ext.lower() == ".png" else ".png"
    fallback_path = f"{base_name}{fallback_ext}"
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path)
    return JSONResponse(content={"detail": "Image not found."}, status_code=404)