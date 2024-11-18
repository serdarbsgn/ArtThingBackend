from sqlalchemy import  delete, func, literal, select, update,desc,not_,exists
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.mysql import insert
from ..sql_dependant.sql_tables import *
from sqlalchemy.sql.functions import coalesce,concat,count

class Select():
    
    def user_project_count(data):
        return select(count(Project.creator_id)).where(Project.creator_id == data["creator_id"])
    
    def user_karma_point_project(data):
        return select(func.sum(Project.likes)).where(Project.creator_id == data["creator_id"])
    
    def user_project_comment_count(data):
        return select(count(ProjectComment.user_id)).where(ProjectComment.user_id == data["user_id"])
    
    def user_karma_point_comment(data):
        return select(func.sum(ProjectComment.likes)).where(ProjectComment.user_id == data["user_id"])

    def projectCommentLikes_exists(data):
        return select(ProjectCommentLikes.l_d).where(ProjectCommentLikes.user_id == data["user_id"],ProjectCommentLikes.comment_id == data["comment_id"])
    
    def projectLikes_exists(data):
        return select(ProjectLikes.l_d).where(ProjectLikes.user_id == data["user_id"],ProjectLikes.project_id == data["project_id"])
    
    def user_username(data):
        statement = select(User.username).where(User.id == data["id"])
        return statement
    
    def user_id_profile_picture_join_date(data):
        return select(User.id.label("creator_id"),User.profile_picture,User.created_at.label("join_date")).where(User.username == data["creator"])

    def user_profile_picture(data):
        return select(User.profile_picture).where(User.username == data["user"])
    
    def creator_projects(data):
        return Select.projects(data).where(Project.creator_id == data["creator_id"])
    
    def projects(data):
        return select(Project.id,User.username.label('creator'),User.id.label('creator_id'),Project.title,Project.created_at,Project.likes).join(User, User.id == Project.creator_id).order_by(Project.created_at).limit(10).offset(data["page"]*10)
    
    def project(data):
        return select(User.username.label('creator'),User.id.label('creator_id'),Project.title,Project.content,Project.likes,Project.created_at).join(User, User.id == Project.creator_id).where(Project.id == data["project_id"])
    
    def creator_projects_count(data):
        return select(count(Project.creator_id)).where(Project.creator_id == data["creator_id"])
    
    def projects_count():
        return select(count(Project.id))
    
    def project_comment(data):
        query = select(ProjectComment.id,ProjectComment.parent_id,ProjectComment.user_id,ProjectComment.content,ProjectComment.likes,ProjectComment.changed_at).where(ProjectComment.id == data["comment_id"])
        if "user_id" in data:
            query = query.where(ProjectComment.user_id == data["user_id"])
        return query
    
    def project_comments(data):
        if "user_id" in data:
            return Select.project_comments_logged_in(data)
        return Select.project_comments_not_logged_in(data)
    
    def project_comments_not_logged_in(data):
        return select(ProjectComment.id,ProjectComment.parent_id,User.username,ProjectComment.content,ProjectComment.likes,ProjectComment.replies,ProjectComment.changed_at,literal(None).label('l_d')).join(User,ProjectComment.user_id == User.id).where(
           ProjectComment.project_id == data["project_id"],ProjectComment.parent_id == data["parent_id"]).order_by(ProjectComment.id).limit(50).offset(data["page"]*50)
    
    def project_comments_logged_in(data):
        return select(ProjectComment.id,ProjectComment.parent_id,User.username,ProjectComment.content,ProjectComment.likes,ProjectComment.replies,ProjectComment.changed_at,ProjectCommentLikes.l_d).join(User,ProjectComment.user_id == User.id).outerjoin(
        ProjectCommentLikes,(ProjectCommentLikes.comment_id == ProjectComment.id) & (ProjectCommentLikes.user_id == data["user_id"])).where(
           ProjectComment.project_id == data["project_id"],ProjectComment.parent_id == data["parent_id"]).order_by(ProjectComment.id).limit(50).offset(data["page"]*50)