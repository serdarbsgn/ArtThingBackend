import uuid
from sqlalchemy import  delete, func, select, update,desc,not_
from sqlalchemy.dialects.mysql import insert
from ..sql_dependant.sql_tables import *
from sqlalchemy.sql.functions import coalesce,concat,count
    
class Update():
    
    def project_user_like(data):
        return update(Project).where(Project.id == data["project_id"]).values(likes = Project.likes + 1)
    
    def project_user_dislike(data):
        return update(Project).where(Project.id == data["project_id"]).values(likes = Project.likes - 1)
    
    def projectComment_user_like(data):
        return update(ProjectComment).where(ProjectComment.id == data["comment_id"]).values(likes = ProjectComment.likes + 1)
    
    def projectComment_user_dislike(data):
        return update(ProjectComment).where(ProjectComment.id == data["comment_id"]).values(likes = ProjectComment.likes - 1)
    
    def projectComment_replies(data):
        return update(ProjectComment).where(ProjectComment.id == data["comment_id"]).values(replies = ProjectComment.replies + data["change"])
    
    def projectComments(data):
        return update(ProjectComment).where(ProjectComment.user_id == data["user_id"],ProjectComment.id == data["comment_id"]).values(content = data["content"],changed_at = func.now())

    
class Delete():

    def projectLikes(data):
        return delete(ProjectLikes).where(
            ProjectLikes.user_id == data["user_id"],ProjectLikes.project_id == data["project_id"],ProjectLikes.l_d == data["l_d"])
    
    def projectCommentLikes(data):
        return delete(ProjectCommentLikes).where(
            ProjectCommentLikes.user_id == data["user_id"],ProjectCommentLikes.comment_id == data["comment_id"],ProjectCommentLikes.l_d == data["l_d"])

    def projectComments(data):
        return delete(ProjectComment).where(ProjectComment.user_id == data["user_id"],ProjectComment.id == data["comment_id"])

    