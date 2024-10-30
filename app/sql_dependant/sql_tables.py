from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, Integer, Text, ForeignKey,String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(25), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    profile_picture = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(String(32),primary_key=True)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text)
    likes = Column(Integer,default = 0)
    created_at = Column(DateTime, default=datetime.now)

class ProjectComment(Base):
    __tablename__ = "project_comments"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer,default=0,nullable=True)
    project_id = Column(String(32), ForeignKey('projects.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text)
    likes = Column(Integer,default=0)
    replies = Column(Integer,default=0)
    changed_at = Column(DateTime, default=datetime.now)

class ProjectCommentLikes(Base):
    __tablename__ = "project_comment_likes"
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, primary_key=True)
    comment_id = Column(Integer, ForeignKey('project_comments.id'), nullable=False, primary_key=True)
    l_d = Column(Enum("Like", "Dislike", name="like_dislike"), default="Like")


class ProjectLikes(Base):
    __tablename__ = "project_likes"
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, primary_key=True)
    l_d = Column(Enum("Like", "Dislike", name="like_dislike"), default="Like")

