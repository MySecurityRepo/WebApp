from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint, CheckConstraint, and_, Column, Integer, String, ForeignKey, DateTime, Enum, Text, func, JSON
from sqlalchemy.dialects.mysql import MEDIUMTEXT, VARCHAR
from sqlalchemy.orm import relationship
from .extensions import db


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)
    
def iso_utc(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

class Thread(db.Model):
    __tablename__ = "threads"
    id               = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    title            = db.Column(db.String(40))
    created_at       = db.Column(db.DateTime, nullable=False, default=utcnow_naive)
    last_message_id  = db.Column(db.BigInteger, db.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    last_message_at  = db.Column(db.DateTime, nullable=True)
    
    
class ThreadUser(db.Model):
    __tablename__ = "thread_users"
    thread_id            = db.Column(db.BigInteger, db.ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True)
    user_id              = db.Column(db.BigInteger, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    last_read_message_id = db.Column(db.BigInteger, nullable=True)
    
    
class Message(db.Model):
    __tablename__ = "messages"
    id        = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.BigInteger, db.ForeignKey("threads.id", ondelete="CASCADE"), index=True, nullable=False)
    sender_id = db.Column(db.BigInteger, db.ForeignKey("user.id", ondelete='CASCADE'), index=True, nullable=False)
    text      = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.BigInteger, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    created_at= db.Column(db.DateTime, nullable=False, default=utcnow_naive)
    sender    = db.relationship("User", primaryjoin="Message.sender_id==User.id", lazy="joined")
    __table_args__ = (db.Index('ix_messages_thread_time', 'thread_id', 'created_at', 'id'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "threadId": self.thread_id,
            "senderId": self.sender_id,
            "sender": getattr(self.sender, "username", None),
            "text": self.text,
            "ts": iso_utc(self.created_at), 
            "parent_id": self.parent_id, 
        }
    
    
class MessageReaction(db.Model):
    __tablename__ = "message_reactions"
    user_id    = db.Column(db.BigInteger, db.ForeignKey("user.id",     ondelete="CASCADE"), primary_key=True)
    message_id = db.Column(db.BigInteger, db.ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    emoji      = db.Column(VARCHAR(16, charset="utf8mb4", collation="utf8mb4_unicode_ci"), nullable=True, default=None)
    created    = db.Column(db.DateTime, nullable=False, default=utcnow_naive)
    
    
    
class MessageAttachment(db.Model):
    __tablename__ = 'message_attachments'
    message_id = Column(db.BigInteger, ForeignKey('messages.id', ondelete="CASCADE"), primary_key=True)
    file_upload_id = Column(db.BigInteger, ForeignKey('file_uploads.id', ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    

class BlockedUsers(db.Model):
    __tablename__ = 'blocked_users'
    blocker_id = db.Column(db.BigInteger, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key = True, nullable=False,)
    blocked_id = db.Column(db.BigInteger, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key = True, nullable=False,)
    created_at = db.Column(DateTime, default=utcnow_naive, nullable=False)
    __table_args__ = (CheckConstraint("blocker_id <> blocked_id", name="no_self_block"),)
    
    
class FavoriteUsers(db.Model):
    __tablename__ = 'favorite_users'
    liker_id = db.Column(db.BigInteger, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key = True, nullable=False,)
    liked_id = db.Column(db.BigInteger, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key = True, nullable=False,)
    created_at = db.Column(DateTime, default=utcnow_naive, nullable=False)
    __table_args__ = (CheckConstraint("liked_id <> liked_id", name="no_self_block"),)


class PostReactions(db.Model):
    __tablename__ = "post_reactions"
    
    user_id  = db.Column(db.BigInteger, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    post_id  = db.Column(db.BigInteger, db.ForeignKey("post.id", ondelete="CASCADE"), primary_key=True)
    value = db.Column(db.SmallInteger, nullable=False)
    created = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    __table_args__ = ( CheckConstraint("value in (-1,0,1)", name="ck_reaction_value"), )
    
    
class PostAttachment(db.Model):
    __tablename__ = 'post_attachments'
    post_id = Column(db.BigInteger, ForeignKey('post.id', ondelete="CASCADE"), primary_key=True)
    file_upload_id = Column(db.BigInteger, ForeignKey('file_uploads.id', ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    

class CommentReactions(db.Model):
    __tablename__ = "comment_reactions"
    
    user_id  = db.Column(db.BigInteger, db.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    comment_id  = db.Column(db.BigInteger, db.ForeignKey("comment.id", ondelete="CASCADE"), primary_key=True)
    value = db.Column(db.SmallInteger, nullable=False) 
    created = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    __table_args__ = ( CheckConstraint("value in (-1,0,1)", name="ck_reaction_value"), )
    
    
class CommentAttachment(db.Model):
    __tablename__ = 'comment_attachments'
    comment_id = Column(db.BigInteger, ForeignKey('comment.id', ondelete="CASCADE"), primary_key=True)
    file_upload_id = Column(db.BigInteger, ForeignKey('file_uploads.id', ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)


class User(db.Model):
    __tablename__ = 'user'
    __table_args__ = (CheckConstraint("lang IN ('en', 'it', 'fr', 'es', 'de', 'pt', 'ru', 'zh', 'ja', 'ar', 'hi')", name="check_post_lang"),)
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(40))
    surname = db.Column(db.String(40))
    age = db.Column(db.Integer)
    bio = db.Column(MEDIUMTEXT)
    likes = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=False)
    sex = db.Column(db.Integer,  default=0)
    reset_token_issued_at = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    is_suspended = db.Column(db.Boolean, default=False)
    is_tobedeleted = db.Column(db.Boolean, default=False)
    lang = Column(db.String(5), nullable=False, default="en")
    is_premium = Column(db.Boolean, nullable=False, default=False)
    subscription_provider = Column(db.String(20), nullable=True, default=None)
    customer_id = Column(db.String(255), unique=True, nullable=True, default=None)
    is_moderated = Column(db.Boolean, nullable=False, default=False)
    moderation_date = db.Column(db.DateTime, default=None, nullable=True)
    delete_request_date = db.Column(db.DateTime, default=None, nullable=True)
     

class BioAttachment(db.Model):
    __tablename__ = 'user_attachments'
    user_id = Column(db.BigInteger, ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    file_upload_id = Column(db.BigInteger, ForeignKey('file_uploads.id', ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    

class Post(db.Model):
    __tablename__ = 'post'
    __table_args__ = ( UniqueConstraint('title', 'author_id', name='uix_title_author'), CheckConstraint("lang IN ('en', 'it', 'fr', 'es', 'de', 'pt', 'ru', 'zh', 'ja', 'ar', 'hi')", name="check_post_lang"),)
    id = db.Column(db.BigInteger, primary_key=True)
    author_id = db.Column(db.BigInteger, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    title = db.Column(db.String(40), nullable=False)
    body = db.Column(MEDIUMTEXT, nullable=False)
    likes = db.Column(db.BigInteger, default=0, server_default="0")
    category = db.Column(db.Integer)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    is_modified = db.Column(db.Boolean, default= False)
    dislikes = db.Column(db.BigInteger, default=0, server_default="0")
    n_comments = db.Column(db.BigInteger, default= 0)
    lang = Column(db.String(5), nullable=False, default="en")
    								     
									     
									     								     
class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.BigInteger, primary_key=True)
    post_id = db.Column(db.BigInteger, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.BigInteger, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.BigInteger, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    created = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    content = db.Column(MEDIUMTEXT, nullable=False)
    likes = db.Column(db.BigInteger, default=0, server_default="0")
    dislikes = db.Column(db.BigInteger, default=0, server_default="0")
    n_replies = db.Column(db.BigInteger, default= 0)
    

class BlacklistedEmails(db.Model):
    __tablename__ = 'blacklisted_emails'
    id = db.Column(db.BigInteger, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    
      
class FileUpload(db.Model):
    __tablename__ = 'file_uploads'

    id = Column(db.BigInteger, primary_key=True)
    user_id = Column(db.BigInteger, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    path = Column(db.String(255), nullable=False)
    w_path = Column(db.String(255), nullable=True, default=None) 
    mime = Column(db.String(64), nullable=False)
    status = Column(db.Enum('pending', 'approved', 'rejected'), default='pending', nullable=False)
    task_id = Column(db.String(100), nullable=True)  
    created_at = Column(db.DateTime, default=utcnow_naive, nullable=False)  
    size_bytes = Column(db.BigInteger, nullable=True)
    width = Column(db.Integer, nullable=True)        
    height = Column(db.Integer, nullable=True)
    duration_sec = Column(db.Integer, nullable=True)  
    variants = Column(JSON, nullable=True)  
    w_variants = Column(JSON, nullable=True, default=None)        
    filename = Column(db.String(80), nullable=True, default=None) 
    thumbnail = Column(db.String(80), nullable=True, default=None)
    is_ondisk = Column(db.Boolean, nullable=False, default=True)
    
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id  = Column(db.BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    actor_id = Column(db.BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    parent_post_id    = Column(db.BigInteger, ForeignKey('post.id', ondelete='CASCADE'), nullable=True)
    parent_post_slug = db.Column(db.String(60), unique=True, nullable=False)
    parent_comment_id = Column(db.BigInteger, ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    parent_text = db.Column(db.String(50), nullable=True) #title in case of the post, content in case of the comment
    comment_id = Column(db.BigInteger, ForeignKey('comment.id', ondelete='CASCADE'), nullable=False)
    action = Column(db.Enum('reply', 'mention'), default='reply', nullable=False)
    is_read = Column(db.Boolean, nullable=False, default=False)
    created_at = Column(db.DateTime, default=utcnow_naive, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "actorId": self.actor_id,
            "parentPostId": self.parent_post_id,
            "parentCommentId": self.parent_comment_id,
            "commentId": self.comment_id,
            "action": self.action,
            "isRead": self.is_read,
            "createdAt": iso_utc(self.created_at), 
        }
        
        
        
    

##############################################Relationships#############################################

#User.blacklisted_from_posts = db.relationship('Post', secondary = 'post_user_blacklist', back_populates = 'blacklisted_users')
User.uploads = db.relationship("FileUpload", back_populates="user", cascade="all, delete-orphan")
#User.blocked_accounts = db.relationship('User', secondary = BlockedUsers.__table__ , primaryjoin = id == BlockedUsers.blocker_id,  secondaryjoin = id == BlockedUsers.blocked_id, backref = db.backref('blockers', lazy = 'dynamic'), lazy = 'dynamic' )
User.reactions = db.relationship("PostReactions", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
User.liked_posts = db.relationship("Post", secondary="post_reactions", primaryjoin=and_(User.id == PostReactions.user_id, PostReactions.value == 1), secondaryjoin=(Post.id == PostReactions.post_id), viewonly=True,)
User.disliked_posts = db.relationship("Post", secondary="post_reactions", primaryjoin=and_(id == PostReactions.user_id, PostReactions.value == -1), secondaryjoin=(Post.id == PostReactions.post_id), viewonly=True,)	

User.comment_reactions = db.relationship("CommentReactions", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
User.liked_comments = db.relationship("Comment", secondary="comment_reactions", primaryjoin=and_(User.id == CommentReactions.user_id, CommentReactions.value == 1), secondaryjoin=(Comment.id == CommentReactions.comment_id), viewonly=True,)
User.disliked_comments = db.relationship("Comment", secondary="comment_reactions", primaryjoin=and_(id == CommentReactions.user_id, CommentReactions.value == -1), secondaryjoin=(Comment.id == CommentReactions.comment_id), viewonly=True,)


Post.author = db.relationship('User', backref=db.backref('posts', cascade="all, delete-orphan", passive_deletes=True)) #this is when we have a foreign key to link them
#Post.blacklisted_users = db.relationship('User', secondary = 'post_user_blacklist', back_populates = 'blacklisted_from_posts') #this is when we don't have a foreign key, we have to build a new model to link them (Post<->User)
#Post.tags = db.relationship('Tag', secondary='post_tag', back_populates='posts')
Post.reactions = db.relationship("PostReactions", back_populates="post", cascade="all, delete-orphan", passive_deletes=True)
Post.likers = db.relationship("User",secondary="post_reactions",primaryjoin=and_(Post.id == PostReactions.post_id, PostReactions.value == 1),secondaryjoin=(User.id == PostReactions.user_id),viewonly=True,)
Post.dislikers = db.relationship("User",secondary="post_reactions",primaryjoin=and_(Post.id == PostReactions.post_id, PostReactions.value == -1),secondaryjoin=(User.id == PostReactions.user_id),viewonly=True,)


#In this post.comments is a list not a query and to coun them you have to do len(post.comments), if you want it be a query
#you can do lazy='dynamic' and can do post.comments.count()
Comment.post = db.relationship('Post', backref=db.backref('comments',  cascade="all, delete-orphan", passive_deletes=True))
Comment.replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[Comment.id]),  cascade="all, delete-orphan", passive_deletes=True, single_parent=True)
Comment.author = db.relationship('User', backref=db.backref('comments',  cascade="all, delete-orphan", passive_deletes=True))
Comment.reactions = db.relationship("CommentReactions", back_populates="comment", cascade="all, delete-orphan", passive_deletes=True)
Comment.likers = db.relationship("User",secondary="comment_reactions",primaryjoin=and_(Comment.id == CommentReactions.comment_id, CommentReactions.value == 1),secondaryjoin=(User.id == CommentReactions.user_id),viewonly=True,)
Comment.dislikers = db.relationship("User",secondary="comment_reactions",primaryjoin=and_(Comment.id == CommentReactions.comment_id, CommentReactions.value == -1),secondaryjoin=(User.id == CommentReactions.user_id),viewonly=True,)

#Tag.posts = db.relationship('Post', secondary='post_tag', back_populates='tags')

FileUpload.user = relationship("User", back_populates="uploads")

PostReactions.user = db.relationship("User", back_populates="reactions") #define: post_reactions.user and user.reactions
PostReactions.post = db.relationship("Post", back_populates="reactions") #define: post_reactions.post and post.reactions


CommentReactions.user = db.relationship("User", back_populates="comment_reactions") #define: post_reactions.user and user.reactions
CommentReactions.comment = db.relationship("Comment", back_populates="reactions") #define: post_reactions.post and post.reactions
#How to query:
    
#1) Does user X like post Y? exists_like = db.session.query(db.exists().where(and_(PostReactions.user_id == user_id, PostReactions.post_id == post_id, PostReactions.value == 1,))).scalar()
#2) Get the like count for a post (DB truth): likes_count = db.session.query(func.count()).select_from(PostReactions).filter(PostReactions.post_id == post_id, PostReactions.value == 1).scalar()
#3) Users who liked a post: users = (User.query.join(PostReactions, User.id == PostReactions.user_id).filter(PostReactions.post_id == post_id, PostReactions.value == 1).all())

    
    
    
