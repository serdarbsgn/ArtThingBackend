from datetime import datetime
from typing import List, Optional

from fastapi.responses import JSONResponse
from .helpers import limit_line_breaks
from .views_api import ProjectsResponse
from .sql_dependant.sql_write import Delete,Update
from .sql_dependant.sql_tables import  ProjectComment, ProjectCommentLikes, ProjectLikes
from .sql_dependant.sql_connection import sqlconn
from .sql_dependant.sql_read import Select
from .utils import check_auth
from .main import app
from fastapi import Query, Request
from pydantic import BaseModel, Field
from html import escape

class UserStatsResponse(BaseModel):
    projectCount: int
    projectKarmaTotal: int
    projectCommentCount: int
    projectCommentKarmaTotal: int

@app.get('/userstats')
async def user_stats(request:Request):
    user_info = check_auth(request)
    with sqlconn() as sql:
        user_project_count = sql.session.execute(Select.user_project_count({"creator_id":user_info["user"]})).mappings().fetchone()["count"]
        user_project_karma = sql.session.execute(Select.user_karma_point_project({"creator_id":user_info["user"]})).mappings().fetchone()["sum"]  or 0
        user_project_comment_count = sql.session.execute(Select.user_project_comment_count({"user_id":user_info["user"]})).mappings().fetchone()["count"]
        user_project_comment_karma = sql.session.execute(Select.user_karma_point_comment({"user_id":user_info["user"]})).mappings().fetchone()["sum"] or 0
        return UserStatsResponse(projectCount=user_project_count,projectKarmaTotal=user_project_karma,projectCommentCount=user_project_comment_count,projectCommentKarmaTotal=user_project_comment_karma)

class CreatorInfoResponse(BaseModel):
    creatorProfilePicture: str
    joinDate: datetime
    projectCount: int
    projectKarmaTotal:int

@app.get('/creator/{username}')
async def creator_info(username:str):
    creator_name = escape(username)
    with sqlconn() as sql:
        creator = sql.session.execute(Select.user_id_profile_picture_join_date({"creator":creator_name})).mappings().fetchone()
        if creator:
            creator_project_count = sql.session.execute(Select.creator_projects_count({"creator_id":creator["creator_id"]})).mappings().fetchone()["count"]
            creator_project_karma = sql.session.execute(Select.user_karma_point_project({"creator_id":creator["creator_id"]})).mappings().fetchone()["sum"] or 0
            return CreatorInfoResponse(creatorProfilePicture=creator["profile_picture"] if creator["profile_picture"] else "pp.jpg",joinDate=creator["join_date"],projectCount=creator_project_count,projectKarmaTotal=creator_project_karma)
        return JSONResponse(content={"detail": "Creator doesn't exist."}, status_code=404)

@app.get('/creator/{username}/projects')
async def creator_projects(username:str,page: int = Query(0, description="Page number for pagination")):
    creator_name = escape(username)
    with sqlconn() as sql:
        creator = sql.session.execute(Select.user_id_profile_picture_join_date({"creator":creator_name})).mappings().fetchone()
        if creator:
            projects = sql.session.execute(Select.creator_projects({"creator_id":creator["creator_id"],"page":page})).mappings().fetchall()
            return ProjectsResponse(projects=projects)
        return JSONResponse(content={"detail": "Creator doesn't exist."}, status_code=404)
    
class MsgResponse(BaseModel):
    msg : str
    
@app.post('/project/{project_id}/like')
async def like_project(request:Request,project_id:str):
    user_info = check_auth(request)
    user_id = user_info["user"]
    with sqlconn() as sql:
        check_l_d_exists = sql.session.execute(Select.projectLikes_exists({"user_id":user_id,"project_id":escape(project_id)})).mappings().fetchone()
        if check_l_d_exists:
            if check_l_d_exists["l_d"] == "Like":
                sql.session.execute(Delete.projectLikes({"user_id":user_id,"project_id":escape(project_id),"l_d":"Like"}))
                sql.session.execute(Update.project_user_dislike({"project_id":escape(project_id)}))
                sql.session.commit()
                return MsgResponse(msg="Unliked")
            elif check_l_d_exists["l_d"] == "Dislike":
                sql.session.execute(Delete.projectLikes({"user_id":user_id,"project_id":escape(project_id),"l_d":"Dislike"}))
                sql.session.execute(Update.project_user_like({"project_id":escape(project_id)}))
                sql.session.commit()
        like = ProjectLikes(
            user_id = user_id,
            project_id = escape(project_id),
            l_d = "Like"
        )
        sql.session.add(like)
        sql.session.execute(Update.project_user_like({"project_id":escape(project_id)}))
        sql.session.commit()
    return MsgResponse(msg="Liked")
    

@app.post('/project/{project_id}/dislike')
async def dislike_project(request:Request,project_id:str):
    user_info = check_auth(request)
    user_id = user_info["user"]
    with sqlconn() as sql:
        check_l_d_exists = sql.session.execute(Select.projectLikes_exists({"user_id":user_id,"project_id":escape(project_id)})).mappings().fetchone()
        if check_l_d_exists:
            if check_l_d_exists["l_d"] == "Like":
                sql.session.execute(Delete.projectLikes({"user_id":user_id,"project_id":escape(project_id),"l_d":"Like"}))
                sql.session.execute(Update.project_user_dislike({"project_id":escape(project_id)}))
                sql.session.commit()
            elif check_l_d_exists["l_d"] == "Dislike":
                sql.session.execute(Delete.projectLikes({"user_id":user_id,"project_id":escape(project_id),"l_d":"Dislike"}))
                sql.session.execute(Update.project_user_like({"project_id":escape(project_id)}))
                sql.session.commit()
                return MsgResponse(msg="Undisliked")
        like = ProjectLikes(
            user_id = user_id,
            project_id = escape(project_id),
            l_d = "Dislike"
        )
        sql.session.add(like)
        sql.session.execute(Update.project_user_dislike({"project_id":escape(project_id)}))
        sql.session.commit()
    return MsgResponse(msg="Disliked")

class ReplyResponse(BaseModel):
    id: int
    parent_id:int
    username:str
    content: str
    likes:int  
    replies: int
    changed_at: datetime
    l_d:str|None

class RepliesResponse(BaseModel):
    replies : List[ReplyResponse]

@app.get('/project/{project_id}/comments', response_model=RepliesResponse)
async def fetch_project_comments(request:Request,project_id:str,parent_id: Optional[int] = 0, page: Optional[int] = 0):
    with sqlconn() as sql:
        data = {"project_id":escape(project_id),"parent_id":parent_id,"page":page}
        try:
            user_info = check_auth(request)
            data["user_id"] = user_info["user"]
        except:
            pass
        replies = sql.session.execute(Select.project_comments(data)).mappings().fetchall()
        return RepliesResponse(replies = replies)
    
class CreateProjectCommentInfo(BaseModel):
    parent_id: Optional[int] = 0
    project_id: str
    content: str = Field(min_length=4)

class MsgResponseWithID(BaseModel):
    msg : str
    id:int
@app.post('/project/comment')
async def create_project_comment(request:Request,create_comment_info:CreateProjectCommentInfo):
    user_info = check_auth(request)
    project_id = create_comment_info.project_id
    parent_id = create_comment_info.parent_id
    comment_content = limit_line_breaks(escape(create_comment_info.content),5)
    with sqlconn() as sql:
        comment = ProjectComment(
            user_id = user_info["user"],
            parent_id = parent_id,
            project_id = project_id,
            content=comment_content)
        sql.session.add(comment)
        sql.session.execute(Update.projectComment_replies({"comment_id":parent_id,"change":1}))
        sql.session.commit()
        return MsgResponseWithID(msg=f"Comment created successfully",id = comment.id)
    
@app.delete('/project/comment')
async def delete_project_comment(request:Request,comment_id:int):
    user_info = check_auth(request)
    user_id = user_info["user"]
    comment_id = comment_id
    with sqlconn() as sql:
        check_comment_exists = sql.session.execute(Select.project_comment({"comment_id":comment_id})).mappings().fetchone()
        if not check_comment_exists:
            return JSONResponse(content={"detail": "You can't delete what doesn't exist."}, status_code=404)
        if not (check_comment_exists["user_id"] == user_id):
            return JSONResponse(content={"detail": "You can't delete a comment someone else created."}, status_code=403)
        sql.session.execute(Delete.projectComments({"user_id":user_id,"comment_id":comment_id}))
        sql.session.execute(Update.projectComment_replies({"comment_id":check_comment_exists["parent_id"],"change":-1}))
        sql.session.commit()
        return MsgResponse(msg="Deleted comment")
    
class UpdateProjectCommentInfo(BaseModel):
    content: str = Field(min_length=4)

@app.put('/project/comment/{comment_id}')
async def update_project_comment(request:Request,comment_id:int,update_comment_info:UpdateProjectCommentInfo):
    user_info = check_auth(request)
    user_id = user_info["user"]
    comment_content = limit_line_breaks(escape(update_comment_info.content),5)
    with sqlconn() as sql:
        check_comment_exists = sql.session.execute(Select.project_comment({"comment_id":comment_id,"user_id":user_id})).mappings().fetchone()
        if not check_comment_exists:
            return JSONResponse(content={"detail": "You can't edit what doesn't exist."}, status_code=404)
        if not (check_comment_exists["user_id"] == user_id):
            return JSONResponse(content={"detail": "You can't edit a comment someone else created."}, status_code=403)
        sql.session.execute(Update.projectComments({"user_id":user_id,"comment_id":comment_id,"content":comment_content}))
        sql.session.commit()
        return MsgResponse(msg="Updated comment")

@app.get('/project/{project_id}/comment/like')
async def like_projectComment(request:Request,comment_id:int):
    user_info = check_auth(request)
    user_id = user_info["user"]
    with sqlconn() as sql:
        def add_like():
            like = ProjectCommentLikes(
                user_id = user_id,
                comment_id = comment_id,
                l_d = "Like"
            )
            sql.session.add(like)
            sql.session.execute(Update.projectComment_user_like({"comment_id":comment_id}))
            sql.session.commit()
        check_l_d_exists = sql.session.execute(Select.projectCommentLikes_exists({"user_id":user_id,"comment_id":comment_id})).mappings().fetchone()
        if check_l_d_exists:
            if check_l_d_exists["l_d"] == "Like":
                sql.session.execute(Delete.projectCommentLikes({"user_id":user_id,"comment_id":comment_id,"l_d":"Like"}))
                sql.session.execute(Update.projectComment_user_dislike({"comment_id":comment_id}))
                sql.session.commit()
                return MsgResponse(msg="Unliked")

            elif check_l_d_exists["l_d"] == "Dislike":
                sql.session.execute(Delete.projectCommentLikes({"user_id":user_id,"comment_id":comment_id,"l_d":"Dislike"}))
                sql.session.execute(Update.projectComment_user_like({"comment_id":comment_id}))
                sql.session.commit()
                add_like()
                return MsgResponse(msg="Liked2")
        add_like()
        return MsgResponse(msg="Liked")
    

@app.get('/project/{project_id}/comment/dislike')
async def dislike_projectComment(request:Request,comment_id:int):
    user_info = check_auth(request)
    user_id = user_info["user"]
    with sqlconn() as sql:
        def add_dislike():
            like = ProjectCommentLikes(
            user_id = user_id,
            comment_id = comment_id,
            l_d = "Dislike"
            )
            sql.session.add(like)
            sql.session.execute(Update.projectComment_user_dislike({"comment_id":comment_id}))
            sql.session.commit()
        check_l_d_exists = sql.session.execute(Select.projectCommentLikes_exists({"user_id":user_id,"comment_id":comment_id})).mappings().fetchone()
        if check_l_d_exists:
            if check_l_d_exists["l_d"] == "Like":
                sql.session.execute(Delete.projectCommentLikes({"user_id":user_id,"comment_id":comment_id,"l_d":"Like"}))
                sql.session.execute(Update.projectComment_user_dislike({"comment_id":comment_id}))
                sql.session.commit()
                add_dislike()
                return MsgResponse(msg="Disliked2")
            elif check_l_d_exists["l_d"] == "Dislike":
                sql.session.execute(Delete.projectCommentLikes({"user_id":user_id,"comment_id":comment_id,"l_d":"Dislike"}))
                sql.session.execute(Update.projectComment_user_like({"comment_id":comment_id}))
                sql.session.commit()
                return MsgResponse(msg="Undisliked")
        add_dislike()
        return MsgResponse(msg="Disliked")
    
