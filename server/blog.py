import re, os, stripe, functools, bleach, magic, traceback, logging, regex, json, typing as t, unicodedata, hmac, hashlib, time
from flask import Blueprint, g, request, session, jsonify, current_app, redirect, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .models import FileUpload, User, BioAttachment, BlockedUsers, FavoriteUsers, Post, PostAttachment, Comment, PostReactions, CommentAttachment, CommentReactions, Notification
from .extensions import db, csrf
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select, update, union_all, exists, or_, and_, case, true, delete
from sqlalchemy.sql import bindparam
from sqlalchemy.orm import joinedload, aliased
from email_validator import validate_email, EmailNotValidError
from .extensions import mail, limiter
from .auth import login_required
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from slugify import slugify
from flask_mail import Message
from PIL import Image
from .auth import is_valid_user, is_valid_password, USER_RE, PWD_RE
from collections import defaultdict
from bs4 import BeautifulSoup
from flask_wtf.csrf import CSRFError
from random import choices
from cachetools import TTLCache
from uuid import uuid4
from urllib.parse import urljoin
import boto3
from pathlib import Path
import subprocess




# Logger for uploads
upload_logger = logging.getLogger("uploads")
upload_logger.setLevel(logging.ERROR)
upload_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/uploads_exceptions.log")
upload_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not upload_logger.hasHandlers():
    upload_logger.addHandler(upload_handler)
    
    
# Logger for blog functions
blog_logger = logging.getLogger("blog")
blog_logger.setLevel(logging.ERROR)
blog_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/blog_exceptions.log")
blog_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not blog_logger.hasHandlers():
    blog_logger.addHandler(blog_handler)
    
    
limit_logger = logging.getLogger("limit")
limit_logger.setLevel(logging.ERROR)
limit_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/limiter_exceptions.log")
limit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not limit_logger.hasHandlers():
    limit_logger.addHandler(limit_handler)


bp = Blueprint('blog', __name__)


###############################################################################################################
###############################################FOR SECURITY####################################################
###############################################################################################################


@bp.app_errorhandler(429) 
def ratelimit_handler(e):
    ip = request.remote_addr
    route = request.url_rule.rule if request.url_rule else request.path
    endpoint = request.endpoint
    method = request.method
    user = getattr(getattr(g, 'user', None), 'username', 'anonymous')

    limit_logger.error(f"[{datetime.utcnow().isoformat()}] | USER={user} | IP={ip} | {method} {route} | endpoint={endpoint} | ERROR=rate_limit_exceeded")
    return jsonify(message="LIMIT_EXCEEDED"), 429


@bp.app_errorhandler(CSRFError)
def handle_csrf(e):
    ip = request.remote_addr
    route = request.url_rule.rule if request.url_rule else request.path
    endpoint = request.endpoint
    method = request.method
    #referrer = request.referrer
    #host = request.host_url 

    user = getattr(getattr(g, 'user', None), 'username', 'anonymous')
    blog_logger.error(f"[{datetime.utcnow().isoformat()}] | USER={user} | IP={ip} | {method} {route} | endpoint={endpoint} | CSRF ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'>
    return '', 403
    
    
    
    
    
###############################################################################################################
################################################Serve Uploads##################################################
###############################################################################################################


WASABI_ENDPOINT = os.getenv('WASABI_ENDPOINT')
WASABI_ACCESS_KEY   = os.getenv('WASABI_ACCESS_KEY')
WASABI_SECRET_KEY   = os.getenv('WASABI_SECRET_KEY')
WASABI_REGION   = os.getenv('WASABI_REGION')
WASABI_BUCKET   = os.getenv('WASABI_BUCKET')
WASABI_PREFIX   = os.getenv('WASABI_PREFIX')


def _remote_key(fname: str, WASABI_PREFIX) -> str:
    return f"{WASABI_PREFIX}/{fname}" if WASABI_PREFIX else fname



@bp.route("/static/uploads/<path:filename>", methods=['GET'])
@limiter.limit("100 per 1 minute")
def serve_upload(filename):
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    local_path = upload_root / filename
    if local_path.is_file():
        return redirect(f"/static/uploads/{filename}", code=302)

    s3 = boto3.client("s3", endpoint_url=WASABI_ENDPOINT, aws_access_key_id=WASABI_ACCESS_KEY, aws_secret_access_key=WASABI_SECRET_KEY, region_name=WASABI_REGION,)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(local_path, "wb") as f:
            s3.download_fileobj(WASABI_BUCKET, _remote_key(filename, WASABI_PREFIX), f)
            
        db.session.query(FileUpload).filter(FileUpload.filename==filename).update({FileUpload.is_ondisk: True}, synchronize_session=False)
        db.session.commit()
        return redirect(f"/static/uploads/{filename}", code=302)

    except Exception as e:
        db.session.rollback()
        try:
            local_path.unlink(missing_ok=True)
        except Exception:
            pass
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
    




###############################################################################################################
#################################################Create User Page##############################################
###############################################################################################################

def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

allowed_tags = [
    'p', 'b', 'i', 'u', 'strong', 'em', 'ul', 'ol', 'li', 'br',
    'a', 'span', 'blockquote', 'attachment',
]

allowed_attrs = {
    'a': ['href', 'target', 'rel'],
    'attachment': ['data-id','data-kind'],
    'span' : ['class'],
}

allowed_protocols = ["https", "mailto"]


def is_effectively_empty(html: str) -> bool:
    if not html or not html.strip():
        return True

    text_only = re.sub(r"<[^>]*>", "", html).strip()
    if text_only:
        return False

    has_img = re.search(r"<img\b", html, re.IGNORECASE)
    has_video = re.search(r"<video\b", html, re.IGNORECASE)
    has_pdf_link = re.search(r'<a\b[^>]*href="[^"]+\.pdf"', html, re.IGNORECASE)

    return not (has_img or has_video or has_pdf_link)
    
    

PUBLIC_BASE_URL = os.getenv('FRONTEND_URL')
def abs_url(path: str) -> str:
    path = "/api/" + path.lstrip("/")
    return urljoin(PUBLIC_BASE_URL, path)    



def serialize_upload(fu):    
    variants = getattr(fu, 'variants', None)
    url = None
    thumbnail = None
    if not variants:
        url = abs_url(f"static/uploads/{os.path.basename(fu.path)}")
        if fu.thumbnail is not None:
            thumbnail = abs_url(f"static/uploads/{os.path.basename(fu.thumbnail)}")
    else:
        for k, v in list(variants.items()):
            variants[k] = abs_url(v)

    return {
        "id": int(fu.id),
        "mime": fu.mime,
        "variants": variants,
        "url": url,
        "w_variants": fu.w_variants,
        "w_path": fu.w_path,
        "width": getattr(fu, 'width', None),
        "height": getattr(fu, 'height', None),
        "duration_sec": getattr(fu, 'duration_sec', None),
        "status": fu.status,
        "name": fu.filename,
        "thumbnail": thumbnail
    }



NAME_RE = NAME_RE = regex.compile(r"^(?:[\p{L}\p{M}]+(?:[ '\-·][\p{L}\p{M}]+)*)?$")
INLINE_MEDIA_RE = re.compile(r'(<img\b|<video\b|<source\b|data:)', re.I)


def is_valid_name(name):
    if not isinstance(name, str):
        return False
    name = unicodedata.normalize('NFC', name.strip())    
    return bool(NAME_RE.fullmatch(name))


@bp.route('/user', methods=['PUT'])
@login_required
@limiter.limit("5 per 15 minutes")
def edit_user():
    
    data = request.get_json(force=True) 
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip()
    surname = (data.get("surname") or "").strip()
    bio = (data.get("bio") or "").strip()
    sex = int(data.get("sex") or 0)
    att_ids   = data.get("attachment_ids") or []
    
    try: 
        age = int(data.get("age") or 0)
    except (TypeError, ValueError):
        return jsonify(message="AGE_NOT_VALID"), 400
    try: 
        user_id = int(data.get("id") or 0)
    except (TypeError, ValueError):
        return '', 400
    
    if user_id != g.user.id:
        return '', 400
    if not is_valid_user(username):
        return jsonify(message="USERNAME_NOT_VALID"), 400
    if username != g.user.username:
        return jsonify(message="USERNAME_NOT_VALID"), 400
    if not email:
        return jsonify(message="EMAIL_NOT_VALID"), 400
    if not is_valid_name(name):
        return jsonify(message="NAME_NOT_VALID"), 400
    if not is_valid_name(surname):
        return jsonify(message="SURNAME_NOT_VALID"), 400
    if not (0 <= int(age) < 120):
        return jsonify(message="AGE_NOT_VALID"), 400
    if not sex in {0, 1, 2}:
        return '', 400
    
    try:
        att_ids = [int(str(i).strip()) for i in att_ids]
    except (TypeError, ValueError) as e:
        return '', 400
                
    if len(att_ids) != len(set(att_ids)):
        return '', 400    
            
    uploads = []        
    if att_ids:
        uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
        found = {u.id for u in uploads}
        missing = [i for i in att_ids if i not in found]
        if missing:
            return '', 400       
        bad = [u.id for u in uploads if u.status != 'approved']
        if bad:
            return '', 400          
        foreign = [u.id for u in uploads if u.user_id != g.user.id]
        if foreign:
            return '', 403

    msg = ''
    email_changed=False 
    if email != g.user.email:      
        try:
            valid = validate_email(email)
            email_form = valid.email
            catched_user = User.query.filter(User.email == email_form).first()
            if catched_user is not None and catched_user.id != g.user.id:
                return jsonify(message="EMAIL_ALREADY_TAKEN"), 400
                          
            g.user.email = email_form
            g.user.is_active = False
            email_changed=True
            msg = "EMAIL_CHANGED"
        except EmailNotValidError as e:
            return jsonify(message="EMAIL_NOT_VALID"), 400       
                     
    try:               
        if INLINE_MEDIA_RE.search(bio):
            return '', 400      
        bio = bleach.clean(bio, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
        g.user.bio = bio
     
        g.user.username = username
        g.user.name = name
        g.user.surname = surname
        g.user.age = age   
        g.user.sex = sex
        
        existing_att = BioAttachment.query.filter_by(user_id=g.user.id).all()
        existing_ids = {pa.file_upload_id for pa in existing_att}
        desired_ids  = set(att_ids)
        
        to_delete = existing_ids - desired_ids
        to_add    = desired_ids - existing_ids
              
        if to_delete:
            BioAttachment.query.filter(BioAttachment.user_id == g.user.id, BioAttachment.file_upload_id.in_(to_delete)).delete(synchronize_session=False)
        if to_add:
            db.session.bulk_save_objects([ BioAttachment(user_id=g.user.id, file_upload_id=fid) for fid in to_add ])
            
        db.session.commit()
        atts = db.session.query(FileUpload).join(BioAttachment, BioAttachment.file_upload_id == FileUpload.id).filter(BioAttachment.user_id == g.user.id).all()        
        
        if email_changed:
            from .celery_tasks import send_verification_email
            send_verification_email.delay(g.user.id)           
            
        data = {
            "id": g.user.id,
            "username": g.user.username,
            "email": g.user.email,
            "name": g.user.name,
            "surname": g.user.surname,
            "age": g.user.age,
            "bio": g.user.bio,
            "sex": g.user.sex,
            "attachments": [serialize_upload(a) for a in atts],
        }      
        
        return jsonify(data=data, message=msg), 200    
            
    except IntegrityError as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 


###############################################################################################################
##############################################Get User By ID###################################################
###############################################################################################################


def is_user_blocked(a: int, b: int) -> bool:
    stmt = select(exists().where(BlockedUsers.blocker_id == a, BlockedUsers.blocked_id == b,))
    return db.session.scalar(stmt)
    
    
def favorite_stats(session, a: int, b: int) -> tuple[int, bool]:    
    stmt = (select(func.count().label("liked_count"), (func.sum(case((FavoriteUsers.liker_id == a, 1), else_=0)) > 0).label("exists_pair"),).where(FavoriteUsers.liked_id == b))
    liked_count, exists_pair = session.execute(stmt).one()
    return int(liked_count), bool(exists_pair)
    
    
def calc_n_favorites(session, b: int) -> int:  
    stmt = (select(func.count().label("liked_count")).where(FavoriteUsers.liked_id == b))
    liked_count = session.scalar(stmt)
    return int(liked_count)
    

@bp.route('/get-user-byid/<int:user_id>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def get_user_by_id(user_id):
    
    try:
        user_id = int(user_id)
        user = User.query.filter_by(id = user_id).first()      
        atts = db.session.query(FileUpload).join(BioAttachment, BioAttachment.file_upload_id == FileUpload.id).filter(BioAttachment.user_id == user_id).all()
        message = ''
    
        if user is None:
            return '', 400
        
        is_blocked = False
        im_blocked = False
        is_favorited = False
                      
        if g.user:
            is_blocked = is_user_blocked(g.user.id, user_id)
            im_blocked = is_user_blocked(user_id, g.user.id)
            n_favorites, is_favorited = favorite_stats(db.session, g.user.id, user_id)
            
            if is_blocked:
                message = "USER_IS_BLOCKED"
                return jsonify(message=message), 403
            if im_blocked:
                message = "IM_BLOCKED"
                return jsonify(message=message), 403
            if user.is_suspended:
                message = "USER_SUSPENDED"
                return jsonify(message=message), 403
            
        else:
            n_favorites = calc_n_favorites(db.session, user_id)
                     
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "surname": user.surname,
            "age": user.age,
            "bio": user.bio,
            "sex": user.sex,
            "is_favorited": is_favorited,
            "n_favorites": n_favorites,
            "attachments": [serialize_upload(a) for a in atts],
        }
        return jsonify(data), 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 
    
   
###############################################################################################################
##############################################Change Language##################################################
###############################################################################################################   
    
@bp.route('/change-language', methods=['PUT'])
@limiter.limit("5 per 30 minutes")
@login_required
def change_language():
    data = request.get_json(silent=True) or {}
    lang = data.get('nextLang')
    
    allowed = {'en','it','fr','es','de','pt','ru','zh','ja','hi'}
    if lang not in allowed:
        return jsonify(message='INVALID_LANG'), 400

    try:
        user = g.user
        if user.lang == lang:
            return jsonify(ok=True, lang=lang), 200

        user.lang = lang
        db.session.commit()
        return jsonify(ok=True, lang=lang), 200

    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
    
    
   
###############################################################################################################
#############################################Modify Password###################################################
###############################################################################################################


@bp.route('/modify-password', methods=['POST'])
@limiter.limit("5 per 30 minutes")
@login_required
def modify_password():
    
        data = request.get_json()  
        old_password = data.get("old_password")
        password1 = data.get("password1")
        password2 = data.get("password2")
        
        if not is_valid_password(password1) or not is_valid_password(password2) or not is_valid_password(old_password):
            return jsonify(message="PASSWORD_NOT_VALID"), 400
        if not check_password_hash(g.user.password, old_password): 
            return jsonify(message="CURRENT_PASSWORD_WRONG"), 400     
        if password1 != password2:
            return jsonify(message="PASSWORD_DONT_CORRESPOND"), 400
        try:
            g.user.password = generate_password_hash(password1, method='pbkdf2:sha256')  
            g.user.reset_token_issued_at = datetime.utcnow()             
            db.session.commit()
            return '', 200
        except IntegrityError as e:
            db.session.rollback()
            blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 400
        
        except Exception as e:
            db.session.rollback()
            blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 500  


###############################################################################################################
##############################################Serialize Post###################################################
###############################################################################################################

def to_iso_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:                      
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_slug(title):
    slug = slugify(title)  
    existing = Post.query.filter(Post.slug.like(f"{slug}%")).all()
    if existing:
        numbers = []
        for post in existing:
            parts = post.slug.rsplit("-", 1)
            if len(parts) > 1 and parts[-1].isdigit():
                numbers.append(int(parts[-1]))
        if numbers:
            new_number = max(numbers) + 1
            slug = f"{slug}-{new_number}"
        else:
            slug = f"{slug}-1"
    return slug       
     

def serialize_post(post):
    post_id = post.id
    author_id = post.author_id
    title = post.title
    category = post.category
    body = post.body
    slug = post.slug
    is_modified = post.is_modified
    likes = post.likes
    created = to_iso_utc(post.created)
    dislikes = post.dislikes
    n_comments = post.n_comments
    
    author_username = db.session.query(User.username).filter(User.id == author_id).scalar()
    atts = (db.session.query(FileUpload).join(PostAttachment, PostAttachment.file_upload_id == FileUpload.id).filter(PostAttachment.post_id == post.id).all())
    
    C = Comment
    B = BlockedUsers
    R = PostReactions
    U = User
    C2 = aliased(C)
    
    viewer_id = getattr(getattr(g, "user", None), "id", None)
    
    if viewer_id is None:   
        not_blocked_parent = true()
        not_blocked_child = true()
        
    else:   
        not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))       
        not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2))
        
        like_sum, dislike_sum = (db.session.query(func.sum(case((R.value == 1, 1), else_=0)), func.sum(case((R.value == -1, 1), else_=0)),).filter(R.post_id == post_id).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id), and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))).one()
        likes    = int(like_sum or 0)
        dislikes = int(dislike_sum or 0)
              
    root_filter = C.parent_id.is_(None)
    seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id == post_id, U.is_suspended.is_(False), root_filter, not_blocked_parent)
    tree = seed.cte(name="visible_tree", recursive=True)
    step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
    tree = tree.union_all(step)
    n_comments = int(db.session.query(func.count()).select_from(tree).scalar() or 0) 
    
    if viewer_id is not None:  
        r = PostReactions.query.get((viewer_id, post_id))
        is_liked   = (r is not None and r.value == 1)
        is_disliked = (r is not None and r.value == -1)
        
    else:
        is_liked = False
        is_disliked = False
        
    data = {"post_id" : post_id, "author_id" : author_id, "title" : title, "category" : category, "body" : body, "slug" : slug,  "is_modified" : is_modified, "likes" : likes, "dislikes" : dislikes, "created" : created, "n_comments" : n_comments, "is_liked" : is_liked, "is_disliked" : is_disliked, "isliking" : False, "isdisliking" : False, "isreplying" : False, "author_username" : author_username, "attachments": [serialize_upload(a) for a in atts],}
    return data



def calc_n_comments(post):
    post_id = post.id
    n_comments = post.n_comments
    
    C = Comment
    B = BlockedUsers
    R = PostReactions
    U = User
    C2 = aliased(C)
    viewer_id = getattr(getattr(g, "user", None), "id", None)
    
    if viewer_id is None:   
        not_blocked_parent = true()
        not_blocked_child = true()
        
    else:
        not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
        not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2))
                       
    root_filter = C.parent_id.is_(None)
    seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id == post_id, U.is_suspended.is_(False), root_filter, not_blocked_parent)
    tree = seed.cte(name="visible_tree", recursive=True)
    step = db.session.query(C2.id, C2.post_id).join(U, U.id == C2.author_id).join(tree, C2.parent_id == tree.c.id).filter(not_blocked_child, U.is_suspended.is_(False))
    tree = tree.union_all(step)
    n_comments = int(db.session.query(func.count()).select_from(tree).scalar() or 0) 
        
    data = {"post_id" : post_id, "n_comments" : n_comments,}
    return data



def calc_likes_post(post):
    post_id = post.id
    likes = post.likes
    dislikes = post.dislikes

    C = Comment
    B = BlockedUsers
    R = PostReactions
    viewer_id = getattr(getattr(g, "user", None), "id", None)
    
    if viewer_id is not None:
    
        like_sum, dislike_sum = (db.session.query(func.sum(case((R.value == 1, 1), else_=0)), func.sum(case((R.value == -1, 1), else_=0)),).filter(R.post_id == post_id).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id), and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))).one()
        
        likes    = int(like_sum or 0)
        dislikes = int(dislike_sum or 0)
    
    if viewer_id is not None:  
        r = PostReactions.query.get((viewer_id, post_id))
        is_liked   = (r is not None and r.value == 1)
        is_disliked = (r is not None and r.value == -1)
        
    else:
        is_liked = False
        is_disliked = False
        
        
    data = {"likes" : likes, "dislikes" : dislikes, "is_liked" : is_liked, "is_disliked" : is_disliked, }
    return data



def fetch_post_info(post):
    post_id = post.id
    author_id = post.author_id
    title = post.title
    slug = post.slug
    
    author_username = db.session.query(User.username).filter(User.id == author_id).scalar()
                
    data = {"post_id" : post_id, "author_id" : author_id, "title" : title, "slug" : slug, "author_username" : author_username, }
    return data


###############################################################################################################
##############################################Get Post By ID###################################################
###############################################################################################################


@bp.route('/get-post/<int:post_id>/<slug>', methods=['GET'])
@limiter.limit("10 per 1 minute")
def get_post_by_id(post_id,slug):
    
    try:
        post_id = int(post_id)
        post = Post.query.join(User, User.id == Post.author_id).filter(Post.id == post_id, User.is_suspended.is_(False)).first()       
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        if post is None:
            return '', 404
        if viewer_id:
            if is_user_blocked(viewer_id, post.author_id):
                message = 'USER_IS_BLOCKED'
                return jsonify(message=message), 403
            elif is_user_blocked(post.author_id, viewer_id):
                message = 'IM_BLOCKED'
                return jsonify(message=message), 403
                           
            if post.slug != slug:
                slug=create_slug(post.title)
                post.slug=slug
                db.session.commit()
                
        data = serialize_post(post)
              
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
    
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
    return jsonify(data), 200



###############################################################################################################
##############################################Create Post######################################################
###############################################################################################################


TITLE_RE = regex.compile(r"^[\p{L}\p{M}\p{Nd}0-9'\"?!,\-._\s]{1,100}$")

def sanitize_title(raw: str) -> str:
    title = unicodedata.normalize("NFC", (raw or "").strip())
    if not bool(TITLE_RE.fullmatch(title)):
        return None
    title = bleach.clean(title, tags=[], attributes={}, strip=True)
    if not (1 <= len(title) <= 40):
        return None
    return title
    

@bp.route('/create-post', methods=['POST'])
@limiter.limit("10 per 10 minutes")
@login_required
def create_post():
    
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    category = int(data.get("category"))
    att_ids   = data.get("attachment_ids") or []
    
    if not title:
        return jsonify(message='TITLE_REQUIRED'), 400              
    if not body and not att_ids:
        return jsonify(message='CONTENT_REQUIRED'), 400   
    if INLINE_MEDIA_RE.search(body):
        return '', 400
              
    try:
        
        title = sanitize_title(title)
        if not title:
            return jsonify(message='TITLE_NOT_ALLOWED'), 400
            
        body = bleach.clean(body, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
        if is_effectively_empty(body) and not att_ids:
            return '', 400
            
        try:
            att_ids = [int(str(i).strip()) for i in att_ids]
        except (TypeError, ValueError):
            return '', 400
                
        if len(att_ids) != len(set(att_ids)):
            return '', 400    
            
        uploads = []
        
        if att_ids:
            uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
            found = {u.id for u in uploads}
            missing = [i for i in att_ids if i not in found]
            if missing:
                return '', 400        
            bad = [u.id for u in uploads if u.status != 'approved']
            if bad:
                return '', 400           
            foreign = [u.id for u in uploads if u.user_id != g.user.id]
            if foreign:
                return '', 403
            
        slug = create_slug(title)                    
        new_post = Post(author_id=g.user.id, title=title, body=body, category=category, likes=0, slug=slug, lang=g.user.lang)
        db.session.add(new_post)
        db.session.flush() 
        
        for u in uploads:
            db.session.add(PostAttachment(post_id=new_post.id, file_upload_id=u.id))
        db.session.commit()        
        serialized = serialize_post(new_post)
        
        return jsonify( post_id=new_post.id, post_slug=new_post.slug, serialized=serialized), 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback() 
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 
        
        

###############################################################################################################
##############################################Modify Post######################################################
###############################################################################################################

@bp.route('/modify-post/<int:post_id>', methods=['PUT'])
@login_required
@limiter.limit("10 per 10 minutes")
def modify_post(post_id):

    data = request.get_json(force=True) 
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    category = int(data.get("category"))
    att_ids   = data.get("attachment_ids") or []
    
    try:
        att_ids = [int(str(i).strip()) for i in att_ids]
    except (TypeError, ValueError):
        return '', 400 
    
    if not title:
            return jsonify(message='TITLE_REQUIRED'), 400
    if not body and not att_ids:
            return jsonify(message='CONTENT_REQUIRED'), 400
    if INLINE_MEDIA_RE.search(body):
            return '', 400
            
    try:
        post_id = int(post_id)
        title = sanitize_title(title)
        if not title:
            return jsonify(message='TITLE_NOT_ALLOWED'), 400
            
        post = Post.query.filter_by(id = post_id).first()
        if post is None:
            return '', 404
        if post.author_id != g.user.id:
            return '', 403                  
        
        body = bleach.clean(body, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
        if is_effectively_empty(body) and not att_ids:
            return '', 400
            
        if len(att_ids) != len(set(att_ids)):
            return '', 400
        
        uploads = []
        if att_ids:
            uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
            found = {u.id for u in uploads}
            missing = [i for i in att_ids if i not in found]
            if missing:
                return '', 400       
            bad = [u.id for u in uploads if u.status != 'approved']
            if bad:
                return '', 400
            foreign = [u.id for u in uploads if u.user_id != g.user.id]
            if foreign:
                return '', 403
             
        
        new_slug = create_slug(title)
        post.title = title
        post.body = body
        post.slug = new_slug
        post.category = category 
        post.is_modified = True
        post.created = utcnow_naive()
        
        existing_att = PostAttachment.query.filter_by(post_id=post.id).all()
        existing_ids = {pa.file_upload_id for pa in existing_att}
        desired_ids  = set(att_ids)
        
        to_delete = existing_ids - desired_ids
        to_add    = desired_ids - existing_ids
        
       
        if to_delete:
            (PostAttachment.query.filter(PostAttachment.post_id == post.id, PostAttachment.file_upload_id.in_(to_delete)).delete(synchronize_session=False))
        if to_add:
          db.session.bulk_save_objects([ PostAttachment(post_id=post.id, file_upload_id=fid) for fid in to_add ])
        
        db.session.commit()
        serialized = serialize_post(post)
        
        return jsonify(post_id=post.id, post_slug=post.slug, serialized=serialized), 200
    
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()   
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 
        
        
        
        

####################################################################################################################
###########################################Retrieve Home Posts######################################################
####################################################################################################################


@bp.route('/retrieve-posts/<int:page>', methods=['GET'])
@limiter.limit("20 per 1 minute")
def retrieve_home_posts(page):

    try:
        per_page = 10
        lang = request.headers.get('X-Lang', 'en')
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User        
        C2 = aliased(C) 
        
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post))
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category != 0, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
         
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val              
                    
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }            
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200       
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
            
####################################################################################################################
###########################################Retrieve Books Posts#####################################################
####################################################################################################################


@bp.route('/retrieve-book-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_book_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')       
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User        
        C2 = aliased(C) 
        
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post)) 
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 1, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
                
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
              
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                                   
                    
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            } 
                  
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200
                    
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
        
####################################################################################################################
###########################################Retrieve Tech Posts#####################################################
####################################################################################################################


@bp.route('/retrieve-tech-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_tech_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post)) 
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 2, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]       
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)      
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                                   
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }           
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200    
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        


####################################################################################################################
###########################################Retrieve Serie Posts#####################################################
####################################################################################################################


@bp.route('/retrieve-serie-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_serie_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post)) 
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 3, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]     
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu) 
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                    
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }    
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200    
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




####################################################################################################################
#############################################Retrieve Art Posts#####################################################
####################################################################################################################


@bp.route('/retrieve-art-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_art_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post)) 
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 4, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]      
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)     
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val          
                    
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }           
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200      
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500



####################################################################################################################
#############################################Retrieve Sport Posts#####################################################
####################################################################################################################


@bp.route('/retrieve-sport-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_sport_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post))
            
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 5, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
               
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                                                       
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            } 
             
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200      
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




####################################################################################################################
#############################################Retrieve Social Posts##################################################
####################################################################################################################


@bp.route('/retrieve-social-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_social_posts(page):

    try:
        per_page = 10       
        lang = request.headers.get('X-Lang', 'en')
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post))
        
        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False),Post.category == 6, Post.lang == lang, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val                  
                    
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }          
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200       
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




####################################################################################################################
###########################################Retrieve Personal Posts##################################################
####################################################################################################################
           

@bp.route('/retrieve-personal-posts/<int:userId>/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
def retrieve_personal_posts(userId, page):
        
    try:
        per_page = 10
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post))

        pagination = (Post.query.join(User, User.id == Post.author_id).filter(User.is_suspended.is_(False), Post.author_id==userId, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                               
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            }           
        
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200        
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
####################################################################################################################
###########################################Retrieve Favorite Posts##################################################
####################################################################################################################
        
        
@bp.route('/retrieve-favorite-posts/<int:page>', methods=['GET'])
@limiter.limit("15 per 1 minute")
@login_required
def retrieve_favorite_posts(page):

    try:
        per_page = 10
        viewer_id  = getattr(getattr(g, "user", None), "id", None)
        
        C = Comment
        R = PostReactions
        B = BlockedUsers
        U = User     
        C2 = aliased(C)
        
        not_blocked_post = true()
        if viewer_id:
            not_blocked_post = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == Post.author_id), and_(B.blocker_id == Post.author_id, B.blocked_id == viewer_id),)).correlate(Post))
        
        pagination = (Post.query.join(User, User.id == Post.author_id).join(FavoriteUsers, db.and_(FavoriteUsers.liked_id == Post.author_id, FavoriteUsers.liker_id == g.user.id)).filter(User.is_suspended.is_(False),Post.category != 0, not_blocked_post).order_by(Post.created.desc(), Post.id.desc()).paginate(page=page, per_page=per_page, error_out=False))
        
        if page > 0 and page > pagination.pages:
            return jsonify({"items" : [] , "has_more": False}), 200
            
        posts = pagination.items
        if not posts:
            return jsonify({"items": [], "has_more": False}), 200
            
        post_ids   = [p.id for p in posts]
        author_ids = [p.author_id for p in posts]
        
        atts = (db.session.query(PostAttachment.post_id, FileUpload).join(FileUpload, FileUpload.id == PostAttachment.file_upload_id).filter(PostAttachment.post_id.in_(post_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)
        
        usernames_by_author = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        
        if viewer_id is None:
            
            not_blocked_parent = true()
            not_blocked_child  = true()
            
        else:
        
            not_blocked_parent = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
            not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)) 
               
        root_filter = C.parent_id.is_(None)
        seed = db.session.query(C.id.label("id"), C.post_id.label("post_id")).join(U, U.id == C.author_id).filter(C.post_id.in_(post_ids), U.is_suspended.is_(False), root_filter, not_blocked_parent)
        tree = seed.cte(name="visible_tree", recursive=True)
        step = db.session.query(C2.id, C2.post_id).join(tree, C2.parent_id == tree.c.id).join(U, U.id == C2.author_id).filter(not_blocked_child, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        visible_comments_by_post = dict(db.session.query(tree.c.post_id, func.count()).select_from(tree).group_by(tree.c.post_id).all()) 
            
        q_reactions = db.session.query(R.post_id, func.sum(case((R.value == 1, 1), else_=0)).label("likes"),func.sum(case((R.value == -1, 1), else_=0)).label("dislikes"),).filter(R.post_id.in_(post_ids))
        if viewer_id is not None:
            q_reactions = q_reactions.filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id),and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))
        reactions_by_post = { pid: {"likes": likes or 0, "dislikes": dislikes or 0} for pid, likes, dislikes in q_reactions.group_by(R.post_id).all()}
        
        user_reaction_by_post = {}
        if viewer_id is not None:
            for pid, val in (db.session.query(R.post_id, R.value).filter(R.post_id.in_(post_ids), R.user_id == viewer_id).all()):
                user_reaction_by_post[pid] = val
                                                     
        def serialize_post_batched(p):
            pid = p.id
            val = user_reaction_by_post.get(pid)
            attachs = attachs_by_comment.get(pid, [])
            return {
                "post_id": pid,
                "author_id": p.author_id,
                "title": p.title,
                "category": p.category,
                "body": p.body,
                "slug": p.slug,
                "is_modified": p.is_modified,
                "likes": reactions_by_post.get(pid, {}).get("likes", 0),
                "dislikes": reactions_by_post.get(pid, {}).get("dislikes", 0),
                "created": to_iso_utc(p.created),
                "n_comments": visible_comments_by_post.get(pid, 0),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "author_username": usernames_by_author.get(p.author_id, ""),
                "attachments": [serialize_upload(a) for a in attachs],
            } 
               
        items = [serialize_post_batched(p) for p in posts]
        
        return jsonify({"items" : items, "has_more": pagination.has_next}), 200        
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500        

        
###############################################################################################################
###########################################Like & Dislike Post#################################################
###############################################################################################################
    
    
@bp.route('/like-post/<int:post_id>', methods=['POST'])
@limiter.limit("15 per 1 minute")
@login_required
def like_post(post_id):

    post = Post.query.get_or_404(post_id)
    
    if post.author_id == g.user.id:
        return '', 400
    
    r = PostReactions.query.get((g.user.id, post_id))
    
    try:
        if r is None: 
            db.session.add(PostReactions(user_id=g.user.id, post_id=post_id, value=1))
        elif r.value == 1:
            db.session.delete(r)
        else:
            r.value = 1
        db.session.commit()
        db.session.refresh(post)
        
        r = calc_likes_post(post)
        likes = int(r["likes"] or 0)
        dislikes = int(r["dislikes"] or 0)
        liked = r["is_liked"]
        disliked = r["is_disliked"]

        return jsonify(liked=liked, disliked=disliked, likes=likes, dislikes=dislikes), 200
            
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()  
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
            
        


@bp.route('/dislike-post/<int:post_id>', methods=['POST'])
@limiter.limit("15 per 1 minute")
@login_required
def dislike_post(post_id):

    post = Post.query.get_or_404(post_id)
    
    if post.author_id == g.user.id:
        return '', 400
    
    r = PostReactions.query.get((g.user.id, post_id))
    
    try:
        if r is None: 
            db.session.add(PostReactions(user_id=g.user.id, post_id=post_id, value=-1))
        elif r.value == -1:
            db.session.delete(r)
        else:
            r.value = -1
        db.session.commit()
        db.session.refresh(post)
        
        r = calc_likes_post(post)
        likes = int(r["likes"] or 0)
        dislikes = int(r["dislikes"] or 0)
        liked = r["is_liked"]
        disliked = r["is_disliked"]

        return jsonify(liked=liked, disliked=disliked, likes=likes, dislikes=dislikes), 200
            
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback() 
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500



###############################################################################################################
################################################Serialize Comment##############################################
###############################################################################################################


def serialize_comment(comment):
    comment_id = comment.id
    post_id = comment.post_id
    author_id = comment.author_id
    parent_id = comment.parent_id
    created = to_iso_utc(comment.created)
    content = comment.content
    likes = comment.likes
    dislikes = comment.dislikes
    n_replies = comment.n_replies
    
    post = db.session.get(Post, post_id)
    author_username = (db.session.query(User.username).filter(User.id == author_id).scalar()) or ""
    atts = (db.session.query(FileUpload).join(CommentAttachment, CommentAttachment.file_upload_id == FileUpload.id).filter(CommentAttachment.comment_id == comment_id).all())
    
    C = Comment
    B = BlockedUsers
    R = CommentReactions
    U = User
    C2 = aliased(C)
    C3 = aliased(C)
    viewer_id = getattr(getattr(g, "user", None), "id", None)    
    
    if viewer_id is None:
    
        not_blocked_child = true()
        not_blocked_child3 = true()
        
    else:
        
        not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2))      
        not_blocked_child3 = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C3.author_id),and_(B.blocker_id == C3.author_id, B.blocked_id == viewer_id),)).correlate(C3))
        like_sum, dislike_sum = (db.session.query(func.sum(case((R.value == 1, 1), else_=0)), func.sum(case((R.value == -1, 1), else_=0)),).filter(R.comment_id == comment_id).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id), and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))).one()
        
        likes    = int(like_sum or 0)
        dislikes = int(dislike_sum or 0)
        
    seed = db.session.query(C2.id.label("id"), C2.post_id.label("post_id")).join(U, U.id == C2.author_id).filter(C2.post_id == post_id, C2.parent_id == comment_id, not_blocked_child, U.is_suspended.is_(False))
    tree = seed.cte(name="visible_tree", recursive=True)            
    step = db.session.query(C3.id, C3.post_id).join(U, U.id == C3.author_id).join(tree, C3.parent_id == tree.c.id).filter(C3.post_id == post_id, U.is_suspended.is_(False), not_blocked_child3)
    tree = tree.union_all(step)
    n_replies = int(db.session.query(func.count()).select_from(tree).scalar() or 0)
    
    if parent_id is not None:
        parent = db.session.get(Comment, parent_id)
        parent_author_id = parent.author_id if parent else None
        parent_username = (db.session.query(User.username).filter(User.id == parent_author_id).scalar()) if parent_author_id else ""
        
    else:
        parent_username = ''
        parent_author_id = post.author_id if post else None
    
    is_parent_blocked = is_user_blocked(author_id, parent_author_id) if parent_author_id else False
    im_blocked_by_parent = is_user_blocked(parent_author_id, author_id) if parent_author_id else False
    post_author_id = post.author_id
    
    if viewer_id is not None:
        r = CommentReactions.query.get((viewer_id, comment_id))
        is_liked   = (r is not None and r.value == 1)
        is_disliked = (r is not None and r.value == -1)
        im_blocked = is_user_blocked(author_id, viewer_id)
        is_blocked = is_user_blocked(viewer_id, author_id)
        
    else:
        is_liked = False
        is_disliked = False
        im_blocked = False
        is_blocked = False
               
    data = {"comment_id" : comment_id, "post_id" : post_id, "author_id" : author_id, "parent_id" : parent_id, "created" : created, "content" : content, "likes" : likes, "dislikes" : dislikes, "n_replies" : n_replies, "is_liked" : is_liked, "is_disliked" : is_disliked, "isliking" : False, "isdisliking" : False, "isreplying" : False, "showchildren" : False, "author_username":author_username, "parent_username":parent_username, "im_blocked":im_blocked, "is_blocked":is_blocked, "is_parent_blocked":is_parent_blocked, "im_blocked_by_parent":im_blocked_by_parent, "parent_author_id":parent_author_id, "post_author_id":post_author_id, "attachments": [serialize_upload(a) for a in atts],}
    return data



def calc_n_replies(comment):
    comment_id = comment.id
    post_id = comment.post_id
    n_replies = comment.n_replies
    
    C = Comment
    B = BlockedUsers
    R = CommentReactions
    U = User
    C2 = aliased(C)
    C3 = aliased(C)
    viewer_id = getattr(getattr(g, "user", None), "id", None)    
    
    if viewer_id is None:
    
        not_blocked_child = true()
        not_blocked_child3 = true()
        
    else:
    
        not_blocked_child3 = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C3.author_id),and_(B.blocker_id == C3.author_id, B.blocked_id == viewer_id),)).correlate(C3))
        not_blocked_child = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id),and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2))      
    
    seed = db.session.query(C2.id.label("id"), C2.post_id.label("post_id")).join(U, U.id == C2.author_id).filter(C2.post_id == post_id, C2.parent_id == comment_id, not_blocked_child, U.is_suspended.is_(False))   
    tree = seed.cte(name="visible_tree", recursive=True)    
    step = db.session.query(C3.id, C3.post_id).join(tree, C3.parent_id == tree.c.id).join(U, U.id == C3.author_id).filter(C3.post_id == post_id, U.is_suspended.is_(False)).filter(not_blocked_child3)
    tree = tree.union_all(step)
   
    n_replies = int(db.session.query(func.count()).select_from(tree).scalar() or 0)
            
    data = {"comment_id" : comment_id, "post_id" : post_id, "n_replies" : n_replies,}
    return data


def calc_likes_comment(comment):
    comment_id = comment.id
    likes = comment.likes
    dislikes = comment.dislikes
    
    
    C = Comment
    B = BlockedUsers
    R = CommentReactions
    viewer_id = getattr(getattr(g, "user", None), "id", None)    
    
    if viewer_id is not None:
    
        like_sum, dislike_sum = (db.session.query(func.sum(case((R.value == 1, 1), else_=0)), func.sum(case((R.value == -1, 1), else_=0)),).filter(R.comment_id == comment_id).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == R.user_id), and_(B.blocker_id == R.user_id, B.blocked_id == viewer_id),)))).one()
        
        likes    = int(like_sum or 0)
        dislikes = int(dislike_sum or 0)     
    
    if viewer_id is not None:   
        r = CommentReactions.query.get((viewer_id, comment_id))
        is_liked   = (r is not None and r.value == 1)
        is_disliked = (r is not None and r.value == -1)
        
    else:
        is_liked = False
        is_disliked = False
             
    data = {"likes" : likes, "dislikes" : dislikes, "is_liked" : is_liked, "is_disliked" : is_disliked,}
    return data



###############################################################################################################
############################################Create Comment For Post############################################
###############################################################################################################


def extract_mentions(html: str) -> list[str]:

    pattern = re.compile(r'<span[^>]*class=["\'][^"\']*\bmention\b[^"\']*["\'][^>]*>@([^<]+)</span>')
    return pattern.findall(html)


@bp.route('/create-comment/<int:post_id>', methods=['POST'])
@login_required
@limiter.limit("20 per 10 minutes")
def create_comment(post_id):

    data = request.get_json(force=True) or {}
    raw = (data.get("content") or "").strip()
    att_ids   = data.get("attachment_ids") or []

    try:
        att_ids = [int(str(i).strip()) for i in att_ids]
    except (TypeError, ValueError) as e:
        return '', 400

    cleaned = bleach.clean(raw, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
    if INLINE_MEDIA_RE.search(cleaned):
        return '', 400
    
    if is_effectively_empty(cleaned) and not att_ids:
        return '', 400
    post = Post.query.get(post_id)
    
    if not post:
        return '', 404
    
    if len(att_ids) != len(set(att_ids)):
        return '', 400    
            
    uploads = []
        
    if att_ids:
        uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
        found = {u.id for u in uploads}
        missing = [i for i in att_ids if i not in found]
        if missing:
            return '', 400        
        bad = [u.id for u in uploads if u.status != 'approved']
        if bad:
            return '', 400
        foreign = [u.id for u in uploads if u.user_id != g.user.id]
        if foreign:
            return '', 403
    
    try:
        new_comment = Comment(post_id=post_id, author_id=g.user.id, content=cleaned)
        db.session.add(new_comment)
        db.session.flush()
        
        post = Post.query.get_or_404(post_id)
        
        if post.author_id != g.user.id:
            new_notification = Notification(user_id=post.author_id, actor_id=g.user.id, parent_post_id=post.id, parent_post_slug=post.slug, parent_text=post.title, comment_id=new_comment.id, action='reply')
            db.session.add(new_notification)
        
        usernames = set(extract_mentions(new_comment.content))
        if usernames:
            usernames.discard(g.user.username)
            rows = (db.session.query(User.username, User.id).filter(User.username.in_(usernames)).all())
            user_map = {u: uid for (u, uid) in rows}
            notifications = []
            for uname in usernames:
                user_id = user_map.get(uname)
                if not user_id:
                    continue
                notifications.append(Notification(user_id=user_id, actor_id=g.user.id, parent_post_id=post.id, parent_post_slug=post.slug, parent_text=post.title, comment_id=new_comment.id, action='mention' ))
            if notifications:
                db.session.add_all(notifications)
                             
        for u in uploads:
            db.session.add(CommentAttachment(comment_id=new_comment.id, file_upload_id=u.id))
        db.session.flush()
            
        payload = serialize_comment(new_comment)
        
        if payload["is_parent_blocked"]:
            db.session.rollback()
            return '', 403
        elif payload["im_blocked_by_parent"]:
            db.session.rollback()
            return '', 403
        
        post_dict = calc_n_comments(post)
        n_comments  = post_dict["n_comments"]
        db.session.commit()

        return jsonify({"n_comments": n_comments, "comment": payload }), 201
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500



###############################################################################################################
#########################################Retrieve Parent Comments##############################################
###############################################################################################################


@bp.route('/retrieve-parent-comments/<int:post_id>/<int:page>', methods=['GET'])
@limiter.limit("20 per 1 minute")
def retrieve_comments(post_id, page):
    try:
        per_page  = 10
        viewer_id = getattr(getattr(g, "user", None), "id", None)
        C  = Comment
        U  = User
        B  = BlockedUsers
        CR = CommentReactions

        post = db.session.get(Post, post_id)
        
        if post is None:
            return '', 400
        post_author_id = post.author_id    
        
        not_blocked_comment = true()
        if viewer_id is not None:   
            not_blocked_comment = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
        
        base_q = (db.session.query(C.id, C.author_id, C.post_id, C.content, C.created, C.likes.label("raw_likes"), C.dislikes.label("raw_dislikes"), C.n_replies.label("raw_n_replies"),).join(U, U.id == C.author_id).filter(C.post_id == post_id,C.parent_id.is_(None), U.is_suspended.is_(False), not_blocked_comment))
        
        base_q = base_q.order_by(C.likes.desc(), C.created.asc(), C.id.asc())
        rows = base_q.limit(per_page + 1).offset(max(page - 1, 0) * per_page).all() 
        has_more = len(rows) > per_page
        parents = rows[:per_page]
        
        if not parents:
            return jsonify({"comment_items": [], "has_more": False}), 200

        parent_ids  = [r.id for r in parents]
        author_ids  = list({r.author_id for r in parents})
        atts = (db.session.query(CommentAttachment.comment_id, FileUpload).join(FileUpload, FileUpload.id == CommentAttachment.file_upload_id).filter(CommentAttachment.comment_id.in_(parent_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)

        usernames = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        reactions_by_comment = {}
        user_react_map = {}
        n_replies_by_parent = {}
        
        C2 = aliased(C)
        C3 = aliased(C)
        
        if viewer_id is None:
        
            not_blocked_C2 = true()
            not_blocked_C3  = true()
            
        else:
        
            q_react = (db.session.query(CR.comment_id,func.sum(case((CR.value == 1, 1), else_=0)).label("likes"),func.sum(case((CR.value == -1, 1), else_=0)).label("dislikes"),).filter(CR.comment_id.in_(parent_ids)).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == CR.user_id),and_(B.blocker_id == CR.user_id, B.blocked_id == viewer_id),)).correlate(CR)))
            
            reactions_by_comment = {cid: {"likes": int(likes or 0), "dislikes": int(dislikes or 0)} for cid, likes, dislikes in q_react.group_by(CR.comment_id).all()}

            for cid, val in (db.session.query(CR.comment_id, CR.value).filter(CR.comment_id.in_(parent_ids), CR.user_id == viewer_id).all()):
                user_react_map[cid] = val

            not_blocked_C2 = ~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id), and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)
            not_blocked_C3 = ~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C3.author_id), and_(B.blocker_id == C3.author_id, B.blocked_id == viewer_id),)).correlate(C3)

      
        seed = db.session.query(C2.id.label("id"), C2.post_id.label("post_id"), C2.parent_id.label("parent_id"), C2.author_id.label("author_id"), C2.parent_id.label("root_id"),).join(U, U.id == C2.author_id).filter(C2.parent_id.in_(parent_ids)).filter(not_blocked_C2, U.is_suspended.is_(False), )
        tree = seed.cte(name="visible_children_tree", recursive=True)
        step = db.session.query(C3.id, C3.post_id, C3.parent_id, C3.author_id, tree.c.root_id).join(U, U.id == C3.author_id).join(tree, C3.parent_id == tree.c.id).filter(not_blocked_C3, U.is_suspended.is_(False),)
        tree = tree.union_all(step)
        n_replies_by_parent = dict(db.session.query(tree.c.root_id, func.count()).select_from(tree).group_by(tree.c.root_id).all())
        
        items = []
        for r in parents:
        
            cid, aid = r.id, r.author_id
            likes = reactions_by_comment.get(cid, {}).get("likes", 0)
            dislikes = reactions_by_comment.get(cid, {}).get("dislikes", 0)
            attachs = attachs_by_comment.get(cid, [])
            n_replies = int(n_replies_by_parent.get(cid, 0))
            val = user_react_map.get(cid)
            
            items.append({
              "comment_id": cid,
              "post_id": post_id,
              "author_id": aid,
              "parent_id": None,
              "created": to_iso_utc(r.created),
              "content": r.content,
              "likes": likes,
              "dislikes": dislikes,
              "n_replies": n_replies,
              "is_liked": (val == 1),
              "is_disliked": (val == -1),
              "isliking": False,
              "isdisliking": False,
              "isreplying": False,
              "showchildren": False,
              "author_username": usernames.get(aid, ""),
              "parent_username": "",                    
              "parent_author_id": post_author_id,
              "post_author_id": post_author_id,
              "attachments": [serialize_upload(a) for a in attachs],
            })

        return jsonify({"comment_items": items, "has_more": has_more}), 200
        
            
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        


###############################################################################################################
##########################################Retrieve Child Comments##############################################
###############################################################################################################


        
@bp.route('/retrieve-child-comments/<int:post_id>/<int:parent_id>/<int:page>', methods=['GET'])
@limiter.limit("25 per 1 minute")
def retrieve_children(post_id, parent_id, page):
    try:
        per_page  = 15
        viewer_id = getattr(getattr(g, "user", None), "id", None)
        C  = Comment
        U  = User
        B  = BlockedUsers
        CR = CommentReactions
        
        parent = db.session.get(Comment, parent_id)
        post = db.session.get(Post, post_id)
        
        if post is None or parent is None:
            return '',400
        
        parent_author_id = parent.author_id
        post_author_id = post.author_id
        parent_username = (db.session.query(U.username).filter(U.id == parent_author_id).scalar()if parent_author_id else "")
        
        not_blocked_comment = true()
        if viewer_id is not None:   
            not_blocked_comment = (~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)).correlate(C))
        
        base_q = (db.session.query(C.id, C.author_id, C.post_id, C.content, C.created, C.likes.label("raw_likes"), C.dislikes.label("raw_dislikes"), C.n_replies.label("raw_n_replies"),).join(U, U.id == C.author_id).filter(C.post_id == post_id,C.parent_id == parent_id, U.is_suspended.is_(False), not_blocked_comment))

        base_q = base_q.order_by(C.created.asc(), C.id.asc())
        rows = base_q.limit(per_page + 1).offset(max(page - 1, 0) * per_page).all()
        has_more = len(rows) > per_page
        children = rows[:per_page]

        if not children:
            return jsonify({"comment_items": [], "has_more": False}), 200

        child_ids  = [r.id for r in children]
        author_ids  = list({r.author_id for r in children})
        atts = (db.session.query(CommentAttachment.comment_id, FileUpload).join(FileUpload, FileUpload.id == CommentAttachment.file_upload_id).filter(CommentAttachment.comment_id.in_(child_ids)).all())
        
        attachs_by_comment = defaultdict(list)
        for cid, fu in atts:
            attachs_by_comment[cid].append(fu)

        usernames = dict(db.session.query(U.id, U.username).filter(U.id.in_(author_ids)).all())
        reactions_by_comment = {}
        user_react_map = {}
        n_replies_by_child = {}
        
        C2 = aliased(C)
        C3 = aliased(C)
        
        if viewer_id is None:
            
            not_blocked_C2 = true()
            not_blocked_C3  = true()            
            
        else:
            q_react = (db.session.query(CR.comment_id,func.sum(case((CR.value == 1, 1), else_=0)).label("likes"),func.sum(case((CR.value == -1, 1), else_=0)).label("dislikes"),).filter(CR.comment_id.in_(child_ids)).filter(~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == CR.user_id),and_(B.blocker_id == CR.user_id, B.blocked_id == viewer_id),)).correlate(CR)))
            
            reactions_by_comment = {cid: {"likes": int(likes or 0), "dislikes": int(dislikes or 0)} for cid, likes, dislikes in q_react.group_by(CR.comment_id).all()}

            for cid, val in (db.session.query(CR.comment_id, CR.value).filter(CR.comment_id.in_(child_ids), CR.user_id == viewer_id).all()):
                user_react_map[cid] = val
        
            not_blocked_C2 = ~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C2.author_id), and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)
            not_blocked_C3  = ~exists().where(or_(and_(B.blocker_id == viewer_id,  B.blocked_id == C3.author_id),and_(B.blocker_id == C3.author_id, B.blocked_id == viewer_id),)).correlate(C3)
            
        seed = db.session.query(C2.id.label("id"), C2.post_id.label("post_id"), C2.parent_id.label("parent_id"), C2.author_id.label("author_id"), C2.parent_id.label("root_id"),).join(U, U.id == C2.author_id).filter(C2.parent_id.in_(child_ids), U.is_suspended.is_(False)).filter(not_blocked_C2)
        tree = seed.cte(name="visible_children_tree", recursive=True)
        step = db.session.query(C3.id, C3.post_id, C3.parent_id, C3.author_id, tree.c.root_id).join(U, U.id == C3.author_id).join(tree, C3.parent_id == tree.c.id).filter(not_blocked_C3, U.is_suspended.is_(False))
        tree = tree.union_all(step)
        n_replies_by_child = dict(db.session.query(tree.c.root_id, func.count()).select_from(tree).group_by(tree.c.root_id).all())
        
        
        items = []
        for r in children:
        
            cid, aid = r.id, r.author_id
            likes = reactions_by_comment.get(cid, {}).get("likes", 0)
            dislikes = reactions_by_comment.get(cid, {}).get("dislikes", 0)
            attachs = attachs_by_comment.get(cid, [])
            n_replies = int(n_replies_by_child.get(cid, 0))
            val = user_react_map.get(cid)                 
            
            items.append({
              "comment_id": cid,
              "post_id": post_id,
              "author_id": aid,
              "parent_id": parent_id,
              "created": to_iso_utc(r.created),
              "content": r.content,
              "likes": likes,
              "dislikes": dislikes,
              "n_replies": n_replies,
              "is_liked": (val == 1),
              "is_disliked": (val == -1),
              "isliking": False,
              "isdisliking": False,
              "isreplying": False,
              "showchildren": False,
              "author_username": usernames.get(aid, ""),
              "parent_username": parent_username or "",                    
              "parent_author_id": post_author_id,
              "post_author_id": post_author_id,
              "attachments": [serialize_upload(a) for a in attachs],
            })

        return jsonify({"comment_items": items, "has_more": has_more}), 200

    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
    except Exception as e:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 


###############################################################################################################
#######################################Retrieve Notification Comments##########################################
###############################################################################################################

def _ancestor_ids_loop(session, parent_id: int):
    if parent_id is None:
        return []
    out = []
    cur = parent_id
    while cur is not None:
        out.append(cur)
        cur = session.execute(select(Comment.parent_id).where(Comment.id == cur)).scalar_one_or_none()
    return out


@bp.route('/retrieve-notification-comments/<int:post_id>/<int:comment_id>', methods=['GET'])
@limiter.limit("15 per 1 minute")
@login_required
def retrieve_notification_comments(post_id, comment_id):
    try:
       
        viewer_id = getattr(getattr(g, "user", None), "id", None)
        C  = Comment
        U  = User
        B  = BlockedUsers
        CR = CommentReactions
        A = CommentAttachment
        F = FileUpload
        
        target_q = (db.session.query(C).join(U, U.id == C.author_id).filter(C.post_id == post_id, C.id == comment_id, U.is_suspended.is_(False)))
        if viewer_id is not None:
            target_q = target_q.filter(~exists().where(or_(and_(B.blocker_id == viewer_id, B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)))
        target_row = target_q.one()
        
        target_comment = serialize_comment(target_row)
        
        ancestor_ids = _ancestor_ids_loop(db.session, target_row.parent_id)
        if not ancestor_ids:
            return jsonify({"target": target_comment}), 200
        
        ordered_ids = list(reversed(ancestor_ids))
        order_case = case({cid: idx for idx, cid in enumerate(ordered_ids)}, value=C.id)
        
        anc_q = (db.session.query(C, U.username).join(U, U.id == C.author_id).filter(C.id.in_(ancestor_ids), C.post_id == post_id, U.is_suspended.is_(False)).order_by(order_case.asc()))
        if viewer_id is not None:
            anc_q = anc_q.filter(~exists().where(or_(and_(B.blocker_id == viewer_id, B.blocked_id == C.author_id), and_(B.blocker_id == C.author_id, B.blocked_id == viewer_id),)))
        anc_rows = anc_q.all()
        
        anc_atts = (db.session.query(A.comment_id, F).join(F, F.id == A.file_upload_id).filter(A.comment_id.in_(ancestor_ids)).all())
        attachs_by_comment = defaultdict(list)
        for cid, fu in anc_atts:
            attachs_by_comment[cid].append(fu)

        reactions_by_comment, user_react_map = {}, {}
        if viewer_id is not None:
            q_react = (db.session.query(CR.comment_id, func.sum(case((CR.value == 1, 1), else_=0)).label("likes"), func.sum(case((CR.value == -1, 1), else_=0)).label("dislikes"),).filter(CR.comment_id.in_(ancestor_ids)).filter(~exists().where(or_(and_(B.blocker_id == viewer_id, B.blocked_id == CR.user_id), and_(B.blocker_id == CR.user_id, B.blocked_id == viewer_id),)).correlate(CR)).group_by(CR.comment_id))
            
            reactions_by_comment = { cid: {"likes": int(likes or 0), "dislikes": int(dislikes or 0)} for cid, likes, dislikes in q_react.all() }
            
            for cid, val in ( db.session.query(CR.comment_id, CR.value).filter(CR.comment_id.in_(ancestor_ids), CR.user_id == viewer_id).all()):
                user_react_map[cid] = val
  
        else:
            q_react = (db.session.query(CR.comment_id,func.sum(case((CR.value == 1, 1), else_=0)).label("likes"),func.sum(case((CR.value == -1, 1), else_=0)).label("dislikes"),).filter(CR.comment_id.in_(ancestor_ids)).group_by(CR.comment_id))          
            reactions_by_comment = {cid: {"likes": int(likes or 0), "dislikes": int(dislikes or 0)} for cid, likes, dislikes in q_react.group_by(CR.comment_id).all()}

        
        def calc_bulk_replies(root_ids: list[int]) -> dict[int, int]:
            if not root_ids:
                return {}
            C2, C3 = aliased(C), aliased(C)
            not_blocked_2 = true()
            not_blocked_3 = true()
            if viewer_id is not None:
                not_blocked_2 = ~exists().where(or_(and_(B.blocker_id == viewer_id, B.blocked_id == C2.author_id), and_(B.blocker_id == C2.author_id, B.blocked_id == viewer_id),)).correlate(C2)
                not_blocked_3 = ~exists().where(or_(and_(B.blocker_id == viewer_id, B.blocked_id == C3.author_id), and_(B.blocker_id == C3.author_id, B.blocked_id == viewer_id),)).correlate(C3)

            seed = (db.session.query(C2.id.label("id"), C2.post_id.label("post_id"), C2.parent_id.label("parent_id"), C2.parent_id.label("root_id"),).join(U, U.id == C2.author_id).filter(C2.parent_id.in_(root_ids), C2.post_id == post_id, U.is_suspended.is_(False), not_blocked_2))
            tree = seed.cte(name="anc_tree", recursive=True)
            step = (db.session.query(C3.id, C3.post_id, C3.parent_id, tree.c.root_id).join(U, U.id == C3.author_id).join(tree, C3.parent_id == tree.c.id).filter(C3.post_id == post_id, U.is_suspended.is_(False), not_blocked_3))
            tree = tree.union_all(step)
            return dict(db.session.query(tree.c.root_id, func.count()).select_from(tree).group_by(tree.c.root_id).all())

        n_replies_by_root = calc_bulk_replies(ancestor_ids)
        post = db.session.get(Post, post_id)
        post_author_id = post.author_id if post else None

        items = []

        for ancestor, anc_username in anc_rows:
            likes = reactions_by_comment.get(ancestor.id, {}).get("likes", 0)
            dislikes = reactions_by_comment.get(ancestor.id, {}).get("dislikes", 0)
            attachs = attachs_by_comment.get(ancestor.id, [])
            val = user_react_map.get(ancestor.id)

            parent_author_id = None            
            parent_username = ""
            if ancestor.parent_id:
                parent_author_id = db.session.query(U.id).filter(U.id == db.session.query(C.author_id).filter(C.id == ancestor.parent_id).scalar()).scalar()
                parent_username = db.session.query(U.username).filter(U.id == parent_author_id).scalar() or ""
                 
            items.append({
                "comment_id": ancestor.id,
                "post_id": ancestor.post_id,
                "author_id": ancestor.author_id,
                "parent_id": ancestor.parent_id,
                "created": to_iso_utc(ancestor.created),
                "content": ancestor.content,
                "likes": likes,
                "dislikes": dislikes,
                "n_replies": int(n_replies_by_root.get(ancestor.id, 0)),
                "is_liked": (val == 1),
                "is_disliked": (val == -1),
                "isliking": False,
                "isdisliking": False,
                "isreplying": False,
                "showchildren": True,
                "author_username": anc_username or "",
                "parent_username": parent_username or "",
                "parent_author_id": post_author_id,
                "post_author_id": post_author_id,
                "attachments": [serialize_upload(a) for a in attachs],
            })

        return jsonify({"target": target_comment, "ancestors": items}), 200

    except IntegrityError:
        db.session.rollback() 
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
    except Exception as e:
        db.session.rollback() 
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




###############################################################################################################
###########################################Like & Dislike Comment##############################################
###############################################################################################################
    
    
@bp.route('/like-comment/<int:comment_id>', methods=['POST'])
@limiter.limit("15 per 1 minute")
@login_required
def like_comment(comment_id):

    comment = Comment.query.get_or_404(comment_id)
    
    if comment.author_id == g.user.id:
        return '', 400
    
    r = CommentReactions.query.get((g.user.id, comment_id))
    
    try:
        if r is None:
            db.session.add(CommentReactions(user_id=g.user.id, comment_id=comment_id, value=1))
        elif r.value == 1:
            db.session.delete(r)
        else:
            r.value = 1
        db.session.commit()
        db.session.refresh(comment)
        r = calc_likes_comment(comment)
        
        likes = int(r["likes"] or 0)
        dislikes = int(r["dislikes"] or 0)
        liked = int(r["is_liked"] or 0)
        disliked = int(r["is_disliked"] or 0)

        return jsonify(liked=liked, disliked=disliked, likes=likes, dislikes=dislikes), 200
            
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()  
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
            


@bp.route('/dislike-comment/<int:comment_id>', methods=['POST'])
@limiter.limit("15 per 1 minute")
@login_required
def dislike_comment(comment_id):

    comment = Comment.query.get_or_404(comment_id)
    
    if comment.author_id == g.user.id:
        return '', 400
    
    r = CommentReactions.query.get((g.user.id, comment_id))
    
    try:
        if r is None: 
            db.session.add(CommentReactions(user_id=g.user.id, comment_id=comment_id, value=-1))
        elif r.value == -1:
            db.session.delete(r)
        else:
            r.value = -1
        db.session.commit()
        db.session.refresh(comment)
        r = calc_likes_comment(comment)
        
        likes = int(r["likes"] or 0)
        dislikes = int(r["dislikes"] or 0)
        liked = int(r["is_liked"] or 0)
        disliked = int(r["is_disliked"] or 0)

        return jsonify(liked=liked, disliked=disliked, likes=likes, dislikes=dislikes), 200
            
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback() 
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




###############################################################################################################
###############################################Reply to a Comment##############################################
###############################################################################################################



def make_preview(html, length=50):
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("attachment"):
        kind = tag.get("data-kind")
        if kind == "image":
            tag.replace_with("🖼️")
        elif kind == "video":
            tag.replace_with("🎬")
        elif kind == "pdf":
            tag.replace_with("📄")
        else:
            tag.decompose()

    text = soup.get_text(" ", strip=True)

    return text[:length-3] + "..." if len(text) > length else text



@bp.route('/reply-comment/<int:parent_id>', methods=['POST'])
@limiter.limit("20 per 10 minutes")
@login_required
def reply_comment(parent_id):

    data = request.get_json(silent=True) or {}
    raw = (data.get("content") or "").strip()
    att_ids   = data.get("attachment_ids") or []

    try:
        att_ids = [int(str(i).strip()) for i in att_ids]
    except (TypeError, ValueError) as e:
        return '', 400
     
    cleaned = bleach.clean(raw, tags=allowed_tags, attributes=allowed_attrs, protocols=allowed_protocols, strip=True)
        
    if INLINE_MEDIA_RE.search(cleaned): 
        return '', 400
    
    if is_effectively_empty(cleaned) and not att_ids:
        return '', 400    
    
    uploads = []
        
    if att_ids:
        uploads = (FileUpload.query.filter(FileUpload.id.in_(att_ids)).all())
        found = {u.id for u in uploads}
        missing = [i for i in att_ids if i not in found]
        if missing:
            return '', 400
        
        bad = [u.id for u in uploads if u.status != 'approved']
        if bad:
            return '', 400
            
        foreign = [u.id for u in uploads if u.user_id != g.user.id]
        if foreign:
            return '', 403
    
    try:

        parent = db.session.execute(select(Comment).where(Comment.id == parent_id).with_for_update()).scalar_one_or_none()
        if not parent:
            return '', 404
           
        parent_user = User.query.get_or_404(parent.author_id)
        parent_username = parent_user.username
            
        post = db.session.execute(select(Post).where(Post.id == parent.post_id).with_for_update()).scalar_one()
        post_slug = post.slug
        post = calc_n_comments(post)
        new_comment = Comment(post_id=parent.post_id, parent_id=parent_id, author_id=g.user.id, content=cleaned)
        db.session.add(new_comment)
        
        n_comments  = int(post["n_comments"] or 0) + 1
        db.session.flush()
        
        if parent.author_id != g.user.id:
            new_notification = Notification(user_id=parent.author_id, actor_id=g.user.id, parent_post_id=parent.post_id, parent_post_slug=post_slug, parent_comment_id=parent.id, parent_text=make_preview(parent.content), comment_id=new_comment.id, action='reply')
            db.session.add(new_notification)
            
        usernames = set(extract_mentions(new_comment.content))
        if usernames:
            usernames.discard(g.user.username)
            rows = (db.session.query(User.username, User.id).filter(User.username.in_(usernames)).all())
            user_map = {u: uid for (u, uid) in rows}
            notifications = []
            for uname in usernames:
                user_id = user_map.get(uname)
                if not user_id:
                    continue
                notifications.append(Notification(user_id=user_id, actor_id=g.user.id, parent_post_id=parent.post_id, parent_post_slug=post_slug, parent_comment_id=parent.id, parent_text=make_preview(parent.content), comment_id=new_comment.id, action='mention' ))
            if notifications:
                db.session.add_all(notifications)
        
        for u in uploads:
            db.session.add(CommentAttachment(comment_id=new_comment.id, file_upload_id=u.id))
        db.session.flush()
        
        ancestor_ids = _ancestor_ids_loop(db.session, parent_id=parent_id)
        ids = list(set(ancestor_ids))
        if ids:
            stmt = (update(Comment).where(Comment.id.in_(ids)).values(n_replies=func.coalesce(Comment.n_replies, 0) + 1).execution_options(synchronize_session=False))
            db.session.execute(stmt)
 
        payload = serialize_comment(new_comment)
        parent = calc_n_replies(parent)
        
        if payload["is_parent_blocked"]:
            db.session.rollback()
            return '', 403
        elif payload["im_blocked_by_parent"]:
            db.session.rollback()
            return '', 403
        
        n_replies = int(parent["n_replies"])
        db.session.commit()

        return jsonify({"n_comments": n_comments, "n_replies":  n_replies, "reply": payload, "ancestors":  ancestor_ids, "parent_username" : parent_username}), 201
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




###############################################################################################################
################################################Delete a Comment###############################################
###############################################################################################################



def child_ids_all(session, root_id: int) -> list[int]:
    out: list[int] = []
    visited: set[int] = set()
    frontier: set[int] = {root_id}

    while frontier:
        rows = session.execute(select(Comment.id).where(Comment.parent_id.in_(frontier))).scalars().all()
        new = [cid for cid in rows if cid not in visited]
        if not new:
            break
        out.extend(new)
        visited.update(new)
        frontier = set(new)

    return out



@bp.route('/delete-comment/<int:comment_id>', methods=['DELETE'])
@limiter.limit("5 per 1 minute")
@login_required
def delete_comment(comment_id: int):
    
    parent_id = None
    post_id = None
    ancestor_ids = []

    s = db.session
    try:    
        comment = s.execute(select(Comment).where(Comment.id == comment_id).with_for_update()).scalar_one_or_none()
        if not comment:
            return '', 404
        parent_id = comment.parent_id
        post_id = comment.post_id
           
        post = s.execute(select(Post).where(Post.id == post_id).with_for_update()).scalar_one()
            
        if comment.author_id != g.user.id and post.author_id != g.user.id:
            return '', 403
                
        descendants = child_ids_all(s, root_id=comment_id)
        ids_to_delete = list(set(descendants) | {comment_id})
        subtree_size = len(ids_to_delete)

        if parent_id is not None:
            ancestor_ids = _ancestor_ids_loop(s, parent_id=parent_id)
            if ancestor_ids:
                _ = s.execute(select(Comment.id).where(Comment.id.in_(ancestor_ids)).with_for_update()).scalars().all()

        s.query(Comment).filter(Comment.id.in_(ids_to_delete)).delete(synchronize_session=False)
        n_comments = s.execute(select(func.count()).select_from(Comment).where(Comment.post_id == post_id)).scalar_one()
        s.execute(update(Post).where(Post.id == post_id).values(n_comments=int(n_comments)))

        if ancestor_ids:
            stmt = update(Comment).where(Comment.id.in_(tuple(ancestor_ids))).values(n_replies=func.greatest(Comment.n_replies - bindparam("delta"), 0))
            s.execute(stmt, {"delta": subtree_size})
        
        n_replies = 0
        if parent_id:
            parent = s.get(Comment, parent_id)
            parent_dict = calc_n_replies(parent)
            n_replies = int(parent_dict["n_replies"] or 0)
        
        s.commit()
        
        post_dictionary = calc_n_comments(post)
        n_comments  = post_dictionary["n_comments"]

        return jsonify({ "n_comments": int(n_comments), "parent_id": parent_id, "n_replies": n_replies, }), 200

    except IntegrityError as ef:
        s.rollback()
        blog_logger.error( f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {ef}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        
        try:
            if post_id is None:
                root = s.get(Comment, comment_id)
                if not root:
                    return '', 404
                post_id = root.post_id
                parent_id = root.parent_id

            ids = child_ids_all(s, root_id=comment_id)
            ids.append(comment_id)
            s.query(Comment).filter(Comment.id.in_(ids)).delete(synchronize_session=False)

            if parent_id is not None:
                ancestor_ids = _ancestor_ids_loop(s, parent_id=parent_id)
                if ancestor_ids:
                    _ = (s.execute(select(Comment.id).where(Comment.id.in_(ancestor_ids)).with_for_update()).scalars().all())

            subtree_size = len(ids)

            n_comments = s.execute(select(func.count()).select_from(Comment).where(Comment.post_id == post_id)).scalar_one()
            s.execute(update(Post).where(Post.id == post_id).values(n_comments=int(n_comments)))

            if ancestor_ids:
                stmt = update(Comment).where(Comment.id.in_(tuple(ancestor_ids))).values(n_replies=func.greatest(Comment.n_replies - bindparam("delta"), 0))
                s.execute(stmt, {"delta": subtree_size})

            n_replies = 0
            if parent_id:
                parent = s.get(Comment, parent_id)
                parent_dict = calc_n_replies(parent)
                n_replies = int(parent_dict["n_replies"] or 0)
            
            s.commit()
            
            post_dictionary = calc_n_comments(post)
            n_comments  = post_dictionary["n_comments"]   

            return jsonify({ "n_comments": int(n_comments), "parent_id": parent_id, "n_replies": n_replies, }), 200

        except Exception as e:
            s.rollback()
            blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 500

    except Exception as e:
        s.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




###############################################################################################################
################################################Delete a Post###############################################
###############################################################################################################


@bp.route('/delete-post/<int:post_id>', methods=['DELETE'])
@limiter.limit("5 per 1 minute")
@login_required
def delete_post(post_id: int):
    s = db.session
    try:
        post = s.execute(select(Post).where(Post.id == post_id).with_for_update()).scalar_one_or_none()
        if not post:
            return '', 404
        if post.author_id != g.user.id:
            return '', 403

        s.delete(post)
        s.commit() 
        return '', 200

    except Exception as e1:
        s.rollback()
        
        post = s.execute(select(Post).where(Post.id == post_id).with_for_update()).scalar_one_or_none()
        if not post:
            return '', 404
        if post.author_id != g.user.id:
            return '', 403

        try:
            
            s.execute(delete(Comment).where(Comment.post_id == post_id))
            s.execute(delete(Post).where(Post.id == post_id))
            s.commit()
            return '', 200

        except Exception as e2:
            
            s.rollback()
            post = s.execute(select(Post).where(Post.id == post_id).with_for_update()).scalar_one_or_none()
            
            if not post:
                return '', 404
            if post.author_id != g.user.id:
                return '', 403
                
            try:
                id_rows = s.execute(select(Comment.id).where(Comment.post_id == post_id).order_by(Comment.id.desc())).scalars().all()
                
                BATCH = 10

                for i in range(0, len(id_rows), BATCH):
                    batch = id_rows[i:i+BATCH]
                    if batch:
                        s.execute(delete(Comment).where(Comment.id.in_(batch)))
                
                s.execute(delete(Post).where(Post.id == post_id))
                s.commit()
                    
                return '', 200
                
            except IntegrityError as ef:
                db.session.rollback()
                blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400

            except Exception as e3:
                db.session.rollback()
                blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e3)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 500


###############################################################################################################
###########################################Search Posts######################################################
###############################################################################################################


@bp.route('/search/posts', methods=['GET'])
@limiter.limit("50 per 1 minute")
@login_required
def search_posts():

    try:
        query = request.args.get("query", "", type=str)
        limit = request.args.get("limit", type=int, default=10)
        
        s = db.session
        if not query:
            return jsonify({"items": []})
            
        query = sanitize_title(query)
       
        rows = select(Post).join(User, User.id == Post.author_id).where(Post.title.ilike(f"%{query}%"), User.is_suspended.is_(False)).limit(limit)
        posts = s.execute(rows).scalars().all()
        posts = [fetch_post_info(post) for post in posts]
        
        items = [{"post_id": post["post_id"], "title": post["title"], "slug": post["slug"], "author_username": post["author_username"] } for post in posts]
        
        return jsonify({"items": items})
        
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
        
        
###############################################################################################################
###########################################Search Users########################################################
###############################################################################################################


@bp.route('/search/users', methods=['GET'])
@limiter.limit("50 per 1 minute")
@login_required
def search_users():

    try:
        query = request.args.get("query", "", type=str)
        limit = request.args.get("limit", type=int, default=10)
        
        s = db.session
        if not query:
            return jsonify({"items": []})
            
        if not is_valid_user(query):
            return jsonify({"items": []})
            
        B = BlockedUsers
        U = User
        
        if g.user is None: 
            not_blocked = true()
        else:
            not_blocked = ~exists().where(or_(and_(B.blocker_id == g.user.id,  B.blocked_id == U.id), and_(B.blocker_id == U.id, B.blocked_id == g.user.id),)).correlate(U)
        
        rows = select(User).where(User.username.ilike(f"%{query}%"), User.is_suspended.is_(False), not_blocked, User.id != 0, User.id != g.user.id ).limit(limit)
        users = s.execute(rows).scalars().all()
        
        items = [{ "id": user.id, "username": user.username,} for user in users]
        
        return jsonify({"items": items})
        
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
        
        
        
###############################################################################################################
###########################################Search Posts In Batches#############################################
###############################################################################################################


@bp.route('/search/posts-batch/<int:page>', methods=['GET'])
@limiter.limit("20 per 1 minute")
@login_required
def search_posts_batch(page):

    try:
        query = request.args.get("q", "", type=str)
        limit = request.args.get("limit", type=int, default=30)
        
        if not query:
            return jsonify({"items": []})
            
        query = sanitize_title(query)
             
        page_obj = Post.query.join(User, User.id == Post.author_id).filter(Post.title.ilike(f"%{query}%"), User.is_suspended.is_(False)).order_by(Post.likes.desc(), Post.created.desc()).paginate(page=page, per_page=limit, error_out=False)
        
        posts = page_obj.items
        posts = [fetch_post_info(post) for post in posts]
        
        items = [{"post_id": post["post_id"], "title": post["title"], "slug": post["slug"], "author_username": post["author_username"], "author_id": post["author_id"], } for post in posts ]
        
        return jsonify({"items": items, "has_more": page_obj.has_next})
        
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
             
###############################################################################################################
###########################################Search Users In Batches#############################################
###############################################################################################################


@bp.route('/search/users-batch/<int:page>', methods=['GET'])
@limiter.limit("20 per 1 minute")
@login_required
def search_users_batch(page):

    try:
        query = request.args.get("q", "", type=str)
        limit = request.args.get("limit", type=int, default=10)
        
        if not query:
            return jsonify({"items": []})
            
        if not is_valid_user(query):
            return jsonify({"items": []})
        
        page_obj = User.query.filter(User.username.ilike(f"%{query}%"), User.is_suspended.is_(False), User.id != 0, User.id != g.user.id).order_by(User.id.desc()).paginate(page=page, per_page=limit, error_out=False)
        users = page_obj.items
        
        items = [{ "id": user.id, "username": user.username, } for user in users]
        
        return jsonify({"items": items})
        
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
             
###############################################################################################################
###########################################Fetch Blocked Users#################################################
###############################################################################################################


@bp.route('/fetch-blocked-users/<int:blocker_id>', methods=['GET'])
@limiter.limit("15 per 1 minute")
@login_required
def fetch_blocked_users(blocker_id):

    try:
        
        s = db.session
        rows = (select(User.id, User.username).join(BlockedUsers,BlockedUsers.blocked_id == User.id).where(BlockedUsers.blocker_id == blocker_id).where(User.is_suspended.is_(False)))
        result = s.execute(rows).all()
        items = [{"user_id": r.id, "username": r.username} for r in result]
        
        return jsonify({"items": items})
        
    except IntegrityError as ef:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:      
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        
        
###############################################################################################################
#############################################Block/Unblock Users###############################################
###############################################################################################################  


@bp.route('/block-user/<int:blocked_id>', methods=['POST'])
@limiter.limit("10 per 1 minute")
@login_required
def block_user(blocked_id: int):
    
    if blocked_id == g.user.id:
        raise ValueError("Cannot block self")
        
    row = BlockedUsers(blocker_id=g.user.id, blocked_id=blocked_id)
    try:
        db.session.add(row)
        db.session.commit()
        
        return jsonify(message='This user has been blocked.'), 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        

@bp.route('/unblock-user/<int:blocked_id>', methods=['DELETE'])
@login_required
@limiter.limit("10 per 1 minute")
def unblock_user(blocked_id: int):
    
    try:
        db.session.query(BlockedUsers).filter_by(blocker_id=g.user.id, blocked_id=blocked_id).delete()
        db.session.commit()
        
        return '', 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500



###############################################################################################################
#########################################Add/Remove User from Favorites########################################
###############################################################################################################  

@bp.route('/add-favorite/<int:liked_id>', methods=['POST'])
@limiter.limit("25 per 1 minute")
@login_required
def add_favorite_user(liked_id: int):
    
    if liked_id == g.user.id:
        raise ValueError("Cannot add himself to favorites")
        
    row = FavoriteUsers(liker_id=g.user.id, liked_id=liked_id)
    try:
        db.session.add(row)
        db.session.commit()
        
        return '', 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
        

@bp.route('/remove-favorite/<int:liked_id>', methods=['DELETE'])
@limiter.limit("25 per 1 minute")
@login_required
def remove_favorite_user(liked_id: int):
    
    try:
        db.session.query(FavoriteUsers).filter_by(liker_id=g.user.id, liked_id=liked_id).delete()
        db.session.commit()
        
        return '', 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500


###############################################################################################################
#############################################Suspend/Delete User###############################################
###############################################################################################################  


def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY3'])  

    
def verify_token(token, expiration=3600):
    serializer = get_serializer()
    try:
        data = serializer.loads(token, max_age=expiration)
        email = data['email']
        ts = data['ts']
    except (BadSignature, SignatureExpired, KeyError):
        return None

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_token_issued_at:
        return None

    if abs(user.reset_token_issued_at.timestamp() - ts) > 1:
        return None  
    return user


def _get_active_subscription(customer_id: str):
    subs = stripe.Subscription.list(customer=customer_id, status="all", limit=10).auto_paging_iter()
    for s in subs:
        if s["status"] in ("active", "trialing", "past_due"):
            return s["id"]
    return None


def suspend_billing():
    user: User = g.user
    if not user.customer_id:
        return

    sub_id = _get_active_subscription(user.customer_id)
    if not sub_id:
        return
    
    stripe.Subscription.update(sub_id, cancel_at_period_end=True,)
    return jsonify({"ok": True})


@bp.route('/suspend-user/<int:user_id>', methods=['POST'])
@limiter.limit("5 per 15 minute")
@login_required
def suspend_user(user_id: int):
    
    data = request.get_json()
    password = data.get("password")
    
    try:
    
        user = User.query.filter_by(id = user_id).first()
        if not check_password_hash(user.password, password):
            return jsonify({"message": "PASSWORD_WRONG"}), 400
            
        #suspend_billing()     
        user.is_suspended = True
        db.session.commit()
        
        return '', 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
    
    

@bp.route('/delete-user/<int:user_id>', methods=['POST'])
@limiter.limit("5 per 15 minute")
@login_required
def delete_user(user_id: int):
    
    data = request.get_json()
    password = data.get("password")
    
    try:
    
        user = User.query.filter_by(id = user_id).first()
        
        if not check_password_hash(user.password, password):
            return jsonify({"message": "PASSWORD_WRONG"}), 400
            
        from .celery_tasks import send_delete_account_email
        send_delete_account_email.delay(user.id)
        
        return '', 200
        
    except IntegrityError as ef:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
        
              
        
@bp.route('/confirm-account-deletion/<token>', methods=['POST']) 
@limiter.limit("5 per 15 minute")
def confirm_account_deletion(token):
    user = verify_token(token)
    
    if user is None:
      return '', 400
    else:
      user.is_suspended = True
      user.is_tobedeleted = True
      #suspend_billing()
      user.reset_token_issued_at = datetime.utcnow()
      user.delete_request_date = datetime.utcnow()
      
      db.session.commit()
      return '', 200



###############################################################################################################
######################################Manage Uploads From Frontend#############################################
###############################################################################################################



ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'ogg', 'pdf', "mov", "heic", "heif"}
MAX_FILE_SIZE = 40 * 1024 * 1024  
MAX_WIDTH, MAX_HEIGHT = 5000, 5000


def allowed_file(filename):
    if filename.count('.') != 1:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    
def detect_mime(file):
    mime = magic.from_buffer(file.read(2048), mime=True)    
    file.seek(0)  
    return mime
    


def save_and_moderate(file_path, mime, user_id, username, ip, filename, thumbnail=None, is_animated=None, width=None, height=None):
    from .celery_tasks import moderate_file_async
    upload = FileUpload(user_id=user_id, path=file_path, mime=mime, status='pending', width=width, height=height, filename=filename, thumbnail=thumbnail)
    db.session.add(upload)
    db.session.commit()
      
    task = moderate_file_async.delay( path=file_path, mime=mime, username=username, ip=ip, filename=filename, is_animated=is_animated )
    upload.task_id = task.id
    db.session.commit()
    
    return upload.id, upload.task_id 
    
    
    
@bp.route('/upload', methods= ['POST'])
@limiter.limit("10 per 1 minute")
@login_required
def upload():
    
    t1 = datetime.utcnow()
    ip =  request.remote_addr
    file = request.files.get('file')
    t2 = datetime.utcnow()
    current_app.logger.debug(f"Time difference: {t2-t1}")
    upload_path = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_path, exist_ok=True)
    file_path = None
    
    if not file:
        return '', 400

    file.seek(0, os.SEEK_END) 
    file_length = file.tell() 
    file.seek(0)
    if file_length > MAX_FILE_SIZE:
        return jsonify({'message': 'FILE_TOO_LARGE'}), 413

    filename = secure_filename(file.filename)
    if not allowed_file(filename):
        return jsonify({'message': 'FILE_NOT_ALLOWED'}), 400

    mime = detect_mime(file)
    if not mime.startswith(('image/', 'video/')) and mime != 'application/pdf':
        return jsonify({'message': 'FILE_NOT_ALLOWED'}), 400
      
    name, ext = os.path.splitext(filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    uid = uuid4().hex

    if mime.startswith('image/'):
        try:
            
            img = Image.open(file)
            is_animated = getattr(img, "is_animated", False)
            
            if (img.width > MAX_WIDTH or img.height > MAX_HEIGHT) and is_animated:
                return jsonify({'message': 'FILE_TOO_LARGE'}), 400
                   
            img.verify()  
            file.seek(0)
            img = Image.open(file)
            img.load()    

            img_no_meta = Image.new(img.mode, img.size)
            img_no_meta.putdata(list(img.getdata()))
            img = img_no_meta.convert('RGB')  
            img.info.pop("exif", None)
            img_width, img_height = (img.width, img.height)

            if is_animated:
                filename = f"{timestamp}_{uid}{ext}" 
                file_path = os.path.join(upload_path, filename)
                file.seek(0)
                file.save(file_path)
                os.chmod(file_path, 0o644)

                try:
                    upload_id, task_id = save_and_moderate( file_path=file_path, mime=mime, user_id=g.user.id, username=g.user.username, ip=ip, filename=filename, is_animated=is_animated, width=img_width, height=img_height )
                except IntegrityError as ef:
                    db.session.rollback()
                    upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                    return '', 400
                except Exception as e:
                    db.session.rollback()
                    upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                    return '', 400    
                          
                return jsonify({'location': f'/static/uploads/{filename}', 'animated': is_animated, 'task_id': task_id, 'upload_id': upload_id, 'status': 'pending', "mime": mime, "name": filename}), 202 
                
            else: 
                
                saved_variants = { }
                sizes = { 'sm': 224, 'md': 500, 'lg': 800}
        
                for label, size in sizes.items():
                    resized_img = img.copy()   
                    resized_img.thumbnail((size, size))
                    filename = f"{timestamp}_{label}_{uid}{ext}"
                    file_path = os.path.join(upload_path, filename)              
                    resized_img.save(file_path, quality=85)
                    os.chmod(file_path, 0o644)

                    if label == 'sm':
                        try:     
                            upload_id, task_id = save_and_moderate(file_path=file_path, mime=mime, user_id=g.user.id, username=g.user.username, ip=ip, filename=filename, width=img_width, height=img_height)
                        except IntegrityError as ef:
                            db.session.rollback()
                            upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                            return '', 400
                        except Exception as e:
                            db.session.rollback()
                            upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                            return '', 400
                   
                    saved_variants[label]=filename
                    
                try:
                    fu = FileUpload.query.get(upload_id)
                    if fu:
                        fu.variants = {k: f"static/uploads/{v}" for k, v in saved_variants.items()}
                        db.session.commit()
                
                except IntegrityError as ef:
                    db.session.rollback()
                    upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")        
                
                except Exception as e:
                    db.session.rollback()
                    upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                
                return jsonify({'variants': {k: f"static/uploads/{v}" for k, v in saved_variants.items()}, 'animated': is_animated, 'task_id': task_id, 'upload_id': upload_id, 'status': 'pending', "mime": mime, "name": saved_variants["sm"]}), 202 
                 
        except Exception as e:
            if file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
            for f in locals().get('saved_variants', {}).values():
                try: os.remove(os.path.join(upload_path, f))
                except: pass       
            upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")     
            return '', 400
                              
    elif mime == 'application/pdf':
        try:
            filename = f"{timestamp}_{uid}{ext}"
            file_path = os.path.join(upload_path, filename)
            file.seek(0)
            file.save(file_path)
            os.chmod(file_path, 0o644)
            try:
                upload_id, task_id = save_and_moderate(file_path=file_path, mime=mime, user_id=g.user.id, username=g.user.username, ip=ip, filename=filename)
            except IntegrityError as ef:
                db.session.rollback()
                upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400
            except Exception as e:
                db.session.rollback()
                upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400
                
            return jsonify({'location': f'static/uploads/{filename}', 'task_id': task_id, 'upload_id': upload_id, 'status': 'pending', "mime": mime, "name": filename}), 202      
        
        except Exception as e:
            os.remove(file_path)
            upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")               
            return '', 400
    
    else:       
    
        try:
            
            if mime not in {"video/mp4", "video/webm", "video/ogg", "video/quicktime"}:
                return jsonify({'message': 'FILE_NOT_ALLOWED'}), 400
            filename = f"{timestamp}_{uid}{ext}"
            thumbnail = f"t{timestamp}_{uid}.jpg"
            file_path = os.path.join(upload_path, filename)
            thumb_path = os.path.join(upload_path, thumbnail)
            file.seek(0)
            file.save(file_path)
            subprocess.run([ "ffmpeg", "-ss", "00:00:01", "-i", file_path, "-frames:v", "1", "-q:v", "2", thumb_path ], check=True, timeout=15)
            os.chmod(file_path, 0o644)
            os.chmod(thumb_path, 0o644)
            
            try:
                upload_id, task_id = save_and_moderate(file_path=file_path, mime=mime, user_id=g.user.id, username=g.user.username, ip=ip, filename=filename, thumbnail=thumbnail)
            except IntegrityError as ef:
                db.session.rollback()
                upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400
            except Exception as e:
                db.session.rollback()
                upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400
            
        except Exception as e:
            if file_path is not None:
                os.remove(file_path)
            upload_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")               
            return '', 400
            
                
        return jsonify({'location': f'static/uploads/{filename}', 'task_id': task_id, 'upload_id': upload_id, 'status': 'pending', "mime": mime, "name": filename}), 202  # 202 = Accepted for processing    
        



###############################################################################################################
######################################API endpoint to check moderation status##################################
###############################################################################################################

@bp.route('/moderation_status/<int:upload_id>', methods=['GET'])
@login_required
@limiter.limit("60 per 1 minute")
def moderation_status(upload_id):
    fu = FileUpload.query.filter_by(id=upload_id, user_id=g.user.id).first()
    if not fu:
        return '', 404
        
    base = {
        'upload_id': fu.id,
        'status': fu.status,
        'mime': fu.mime,
        'width': getattr(fu, 'width', None),
        'height': getattr(fu, 'height', None),
        'duration_sec': getattr(fu, 'duration_sec', None),   
    }

    if fu.status=='approved':     
        variants = getattr(fu, 'variants', None)
        url = None
        location = None
        thumbnail = None
        if not variants:
            url = abs_url(f"static/uploads/{os.path.basename(fu.path)}")
            if fu.thumbnail is not None:
                thumbnail = abs_url(f"static/uploads/{os.path.basename(fu.thumbnail)}")
        else:
            for k, v in list(variants.items()):
                variants[k] = abs_url(v)
        
        return jsonify({**base, 'variants': variants or None, 'location': url, "thumbnail": thumbnail}), 200
        
    elif fu.status=='rejected':      
        return jsonify({**base, 'message': 'Upload was rejected due to content policy.'}), 200
    else:
        return jsonify(base), 200



###############################################################################################################
######################################Cache if coming from uploads#############################################
###############################################################################################################

@bp.after_app_request
def add_cache_headers(response):
    if request.path.startswith('/static/uploads/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response



###############################################################################################################
############################################Stripe Subscription################################################
###############################################################################################################


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

PREMIUM_TRUE = {"active", "trialing", "past_due"}
PREMIUM_FALSE = {"canceled", "incomplete", "incomplete_expired", "unpaid", "paused"}



@bp.route("/billing/create-checkout-session", methods=['POST'])
@login_required
@limiter.limit("10 per 1 minute")
def create_checkout_session():
    
    try:
        user = g.user
        if not user.customer_id:
            cust = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
            user.customer_id = cust.id
            user.subscription_provider = "stripe"
            db.session.commit()

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=user.customer_id,              
            line_items=[{"price": os.getenv("STRIPE_PRICE_ID"), "quantity": 1}],
            success_url=f'{os.getenv("FRONTEND_URL")}/subscription_done',
            cancel_url=f'{os.getenv("FRONTEND_URL")}/',
            allow_promotion_codes=True,
            automatic_tax={"enabled": True},
            client_reference_id=str(user.id),          
        )
        return jsonify({"url": session.url})
    
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
    

@bp.route("/billing/portal", methods=['POST'])
@login_required
@limiter.limit("10 per 1 minute")
def billing_portal():
    try:
        user = g.user
        if not (user.customer_id and user.subscription_provider == "stripe"):
            return '', 400

        session = stripe.billing_portal.Session.create(customer=user.customer_id,return_url=f"{os.getenv('FRONTEND_URL')}/subscription_cancellation_done")
        return jsonify({"url": session.url})
        
    except Exception as e:
        db.session.rollback()
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500


@bp.route('/stripe/webhook', methods=['POST'])
@csrf.exempt
@limiter.limit("30 per 1 minute")
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig, secret=WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        return '', 400

    t = event["type"]
    obj = event["data"]["object"]
    
    if t in ("customer.subscription.created", "customer.subscription.updated"):
        customer_id = obj["customer"]
        status = obj["status"]
        user = db_session.query(User).filter_by(customer_id=customer_id).one_or_none()
        if user:
            user.is_premium = status in PREMIUM_TRUE
            db_session.commit()
            
    elif t == "customer.subscription.deleted":
        customer_id = obj["customer"]
        user = db_session.query(User).filter_by(customer_id=customer_id).one_or_none()
        if user:
            user.is_premium = False
            user.customer_id = None
            user.subscription_provider = ""
            db_session.commit()
            
    elif t == "checkout.session.completed":
        customer_id = obj.get("customer")
        client_ref_id = obj.get("client_reference_id")
        if customer_id and client_ref_id:
            user = db_session.get(User, int(client_ref_id))
            if user and not user.customer_id:
                user.customer_id = customer_id
                db_session.commit()
                
    return "", 200







###############################################################################################################
#############################################Advertisements####################################################
###############################################################################################################

ALLOWED_ADS = ['general', 'books', 'tech', 'movies', 'sports', 'music', 'events']
ALLOWED_SLOTS = ['books_mobile_224x150', 'books_tablet_320x400', 'books_desktop_500x630', 'events_mobile_224x150', 'events_tablet_320x400', 'events_desktop_500x630', 'movies_mobile_224x150',
                 'movies_tablet_320x400', 'movies_desktop_500x630', 'general_mobile_224x150', 'general_tablet_320x400', 'general_desktop_500x630', 'music_mobile_224x150', 'music_tablet_320x400', 'music_desktop_500x630', 'sports_mobile_224x150', 'sports_tablet_320x400', 'sports_desktop_500x630', 'tech_mobile_224x150', 'tech_tablet_320x400', 'tech_desktop_500x630', ] 


AD_TYPE_ENABLED = []
AD_LANG_ENABLED = []


def _load_ads(ad_type):
    if not ad_type in ALLOWED_ADS:
        return None
    path = os.path.join(current_app.root_path, f"ads_{ad_type}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        blog_logger.error(f"[{datetime.utcnow()}] USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return None


def _log(line):
    path = "logs/ads.log"
    with open(path, "a") as f:
        f.write(line + "\n")


SECRET = b'osYSSDuXAZf8P067LIOb_Kfdyc81LgV3qiMaocyLzOY'
VIDEO_EXTENSIONS = ['mp4', 'webm',]
IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']


def sign(cid: str, issued_at: int) -> str:
    payload = f"{cid}:{issued_at}".encode()
    return hmac.new(SECRET, payload, hashlib.sha256).hexdigest()


@bp.route('/ad-enabled', methods=['GET'])
@limiter.limit("60 per 1 minute")
def api_ad_enabled():
    ad_type = request.args.get("ad_type")
    lang = request.args.get("lang")
    if not ad_type or not lang:
        return jsonify({"enabled": False}), 200

    if ad_type not in AD_TYPE_ENABLED:
        return jsonify({"enabled": False}), 200

    if lang not in AD_LANG_ENABLED:
        return jsonify({"enabled": False}), 200

    return jsonify({"enabled": True}), 200


@bp.route('/ad', methods=['GET'])
@limiter.limit("60 per 1 minute")
def api_ad():
    slot = request.args.get("slot", "books_sidebar_300x250")
    if slot not in ALLOWED_SLOTS:
        return None
    ad_type = request.args.get("ad_type")
    lang = request.args.get("lang")  
    data = _load_ads(ad_type)
    data = data[lang]
    items = data.get(slot, [])
    if not items:
        return jsonify({"ad": None})

    weights = [i.get("weight", 1) for i in items]
    creative = choices(items, weights=weights, k=1)[0]
    issued_at = int(time.time()) 
    href = f"/r/{ad_type}/{lang}/{creative['id']}"
    content = creative["content"]
    extension = content.split(".")[1]
    
    if extension in VIDEO_EXTENSIONS:
        kind = 'video'
    elif extension in IMAGE_EXTENSIONS:
        kind = 'image'
    
    return jsonify({
        "ad": {
            "id": creative["id"],
            "content": content,
            "kind": kind,
            "href": href,
            "lang": lang,
            "title": creative.get("title"),
            "width": creative.get("width", 300),
            "height": creative.get("height", 250),
            "cid": creative["id"],
            "ad_type": ad_type,
            "issued_at": issued_at,
            "sig": sign(creative["id"], issued_at)
        }
    })



@bp.route('/r/<ad_type>/<lang>/<cid>', methods=['GET'])
@limiter.limit("20 per 1 minute")
def redirect_click(ad_type, lang, cid):
    data = _load_ads(ad_type)
    data = data[lang]

    target = None
    for slot, items in data.items():
        for c in items:
            if c["id"] == cid:
                target = c["href"]
                break
    ts = datetime.utcnow().isoformat()
    _log(f"click, {ts}, {ad_type}, {lang}, {cid}")
    return redirect(target or "/")



seen_tokens = TTLCache(maxsize=50000, ttl=2*60*60)

def verify(cid: str, issued_at: int, sig: str) -> bool:
    now = int(time.time())
    if abs(now - issued_at) > 2*60*60:
        return False
    expected = sign(cid, issued_at)
    return hmac.compare_digest(expected, sig)


def daily_hash(ip: str, salt: str) -> str:
    day = time.strftime("%Y%m%d", time.gmtime())
    return hashlib.sha256(f"{ip}{day}{salt}".encode()).hexdigest()[:16]
    

@bp.post("/impression")
@limiter.limit("60 per 1 minute")
def impression():
    #origin = request.headers.get("Origin") or ""
    #referer = request.headers.get("Referer") or ""
    #if not (origin.startswith("https://yourdomain.com") or referer.startswith("https://yourdomain.com")):
    #    return '', 403

    data = request.get_json(force=True, silent=True) or {}
    cid = data.get("cid"); ad_type = data.get("ad_type"); issued_at = int(data.get("issued_at", 0)); sig = data.get("sig", ""); lang = data.get("lang")

    if not cid or not sig or not issued_at or not verify(cid, issued_at, sig):
        return '', 400

    token_key = f"{cid}:{issued_at}"
    if token_key in seen_tokens:
        return ("", 204)
    seen_tokens[token_key] = True

    #h = daily_hash(request.remote_addr or "0.0.0.0", "your-salt")
    ts = datetime.utcnow().isoformat()
    _log(f"impression, {ts}, {ad_type}, {lang}, {cid}")
    return ("", 204)  

