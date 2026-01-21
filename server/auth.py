import functools
from flask import Blueprint, flash, g, request, session, current_app, jsonify, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from .extensions import db
from .models import User, BlacklistedEmails
from sqlalchemy.exc import IntegrityError
from email_validator import validate_email, EmailNotValidError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .extensions import limiter
from datetime import datetime
from flask_wtf.csrf import generate_csrf
from .extensions import csrf
from flask_wtf.csrf import CSRFError
import logging
import traceback
import regex
import unicodedata

bp = Blueprint('auth', __name__, url_prefix='/auth')

def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Logger for auth
auth_logger = logging.getLogger("auth")
auth_logger.setLevel(logging.ERROR)
auth_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/auth_exceptions.log")
auth_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not auth_logger.hasHandlers():
    auth_logger.addHandler(auth_handler)


limit_logger = logging.getLogger("limit")
limit_logger.setLevel(logging.ERROR)
limit_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/limiter_exceptions.log")
limit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not limit_logger.hasHandlers():
    limit_logger.addHandler(limit_handler)


@bp.app_errorhandler(429)
def ratelimit_handler(e):
    ip = request.remote_addr
    route = request.url_rule.rule if request.url_rule else request.path
    endpoint = request.endpoint
    method = request.method
    user = getattr(getattr(g, 'user', None), 'username', 'anonymous')

    limit_logger.error(f"[{datetime.utcnow().isoformat()}] | USER={user} | IP={ip} | {method} {route} | endpoint={endpoint} | ERROR='Rate Limit Exceeded'")
    return jsonify(message="LIMIT_EXCEEDED"),429


@bp.app_errorhandler(CSRFError)
def handle_csrf(e):
    ip = request.remote_addr
    route = request.url_rule.rule if request.url_rule else request.path
    endpoint = request.endpoint
    method = request.method
    #referrer = request.referrer
    #host = request.host_url
    user = getattr(getattr(g, 'user', None), 'username', 'anonymous')
    
    auth_logger.error(f"[{datetime.utcnow().isoformat()}] | USER={user} | IP={ip} | {method} {route} | endpoint={endpoint} | CSRF ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'>
    return '', 403

###############################################################################################################
################################################Registration###################################################
###############################################################################################################

USER_RE = regex.compile(r'^[\p{L}_][\p{L}\p{M}\p{Nd}_]{1,19}$')
PWD_RE  = regex.compile(r'^(?:(?=.*\p{Ll})|(?=.*\p{Lo}))(?:(?=.*\p{Lu})|(?=.*\p{Lo}))(?=.*\p{Nd})(?=.*[\p{P}\p{S}])(?!.*\s).{10,64}$')


def is_valid_user(username):
    if not isinstance(username, str):
        return False
    username = unicodedata.normalize('NFC', username.strip())    
    return bool(USER_RE.fullmatch(username))


def is_valid_password(password):
    if not isinstance(password, str):
        return False
    password = unicodedata.normalize('NFC', password)
    return bool(PWD_RE.fullmatch(password))
    
    
@bp.route('/register', methods=['POST'])
@limiter.limit("5 per 30 minutes")
def register():

    data = request.get_json() 
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password")  
    
    if not is_valid_user(username):
        return jsonify(message="USERNAME_NOT_VALID"), 400
    elif not is_valid_password(password):
        return jsonify(message="PASSWORD_NOT_VALID"), 400
    else:
        try:
            valid = validate_email(email, allow_smtputf8=True)
            email_form = valid.email
        except EmailNotValidError as e:
            return jsonify(message="EMAIL_NOT_VALID"), 400
            
            
    if db.session.query(BlacklistedEmails).filter(BlacklistedEmails.email == email_form).first():
        return '', 400
    
    lang = request.headers.get('X-Lang', 'en')
    
    try:
        from .celery_tasks import send_verification_email
        new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'), email=email_form, lang=lang)
        db.session.add(new_user)
        db.session.commit()       
        send_verification_email.delay(new_user.id)
        return '', 201
                
    except IntegrityError as e:
    
        db.session.rollback()
        if 'username' in str(e.orig):             
            
            catched_user = User.query.filter_by(username = new_user.username).first()   
            if catched_user is not None:                                                     
                return jsonify(message="USERNAME_ALREADY_TAKEN"), 400          
            else:
                return '', 400
                                                 
        elif 'email' in str(e.orig):
                
            catched_user = User.query.filter_by(email = new_user.email).first()
            if catched_user is not None:
                return jsonify(message="EMAIL_ALREADY_TAKEN"), 400
            else:
                return '', 400
                        
        else:
            auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 400
                        
    except Exception as e:      
        db.session.rollback()
        auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}") 
        return '', 500  


    
###############################################################################################################
################################################CSRF Token Route###############################################
###############################################################################################################


@bp.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    session["ws_csrf"] = token
    response = make_response(jsonify({'csrf_token': token}))
    response.headers['Cache-Control'] = 'no-store'
    return response


###############################################################################################################
######################################Resend verification Email################################################
###############################################################################################################


@bp.route('/resend-email', methods=['POST'])
@limiter.limit("5 per 30 minutes")
def resend_email():
    data = request.get_json()
    email = (data.get("email") or "").strip()
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return jsonify(message="EMAIL_NOT_VALID"), 400
        
    user = User.query.filter_by(email = email).first()
    if user is None:
        return jsonify(message="USER_NOT_FOUND"), 400
    else:
        if user.is_active:
            return jsonify(message="USER_ALREADY_ACTIVE"), 201
        else:
            from .celery_tasks import send_verification_email
            send_verification_email.delay(user.id)
            return '', 201
      

###############################################################################################################
#############################################Email Confirmation################################################
###############################################################################################################

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])  


def verify_token(token, expiration=3600):
    serializer = get_serializer()
    try:
        data = serializer.loads(token, max_age=expiration)
        email = data['email']
        ts = data['ts']
    except (BadSignature, SignatureExpired, KeyError) as e:
        return None

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_token_issued_at:
        return None

    if abs(user.reset_token_issued_at.timestamp() - ts) > 1:
        return None  
    return user


@bp.route('/confirm/<token>', methods=['GET'])
@limiter.limit("5 per 30 minutes")
def confirm_email(token):
    user = verify_token(token)
    
    if user is None:
      return '', 400
    else:
      if user.is_active:
        return '', 200
      user.is_active = True
      user.reset_token_issued_at = datetime.utcnow()
      db.session.commit()
      return '', 200
        



###############################################################################################################
################################################Login##########################################################
###############################################################################################################



@bp.route('/login', methods=['POST'])
@limiter.limit("5 per 10 minutes")
def login():
    
    try: 
        data = request.get_json() 
        username_or_email = (data.get("username_or_email") or "").strip()
        password = data.get("password")
        remember_me = data.get("remember_me")
    
        user = None
        if '@' in username_or_email:
        
            try:
                valid = validate_email(username_or_email, allow_smtputf8=True)
                email_form = valid.email
            except EmailNotValidError as e:
                return jsonify(message="USERNAME_OR_PASSWORD_NOT_VALID"), 400 
                
            user = User.query.filter_by(email = email_form).first()                      
            
        else:
        
            if not is_valid_user(username_or_email):
                return jsonify(message="USERNAME_OR_PASSWORD_NOT_VALID"), 400
        
            user = User.query.filter_by(username = username_or_email).first()

        if user is None:
            return jsonify(message="USERNAME_OR_PASSWORD_NOT_VALID"), 400
        elif not check_password_hash(user.password, password): 
            return jsonify(message="USERNAME_OR_PASSWORD_NOT_VALID"), 400
        elif not user.is_active:
            return jsonify(message="USER_NOT_ACTIVE"), 400
            
        if user.is_moderated and user.moderation_date:
            days_diff = max(0, 7 - ((datetime.utcnow() - user.moderation_date).days + 1))
            
            if days_diff==1:
                return jsonify(message="USER_IS_MODERATED_1"), 400
            else:
                return jsonify(message="USER_IS_MODERATED", days=days_diff), 400
            
        if user.is_suspended or user.is_tobedeleted:
            user.is_suspended = False
            user.is_tobedeleted = False
            db.session.commit()
  
        session.clear()                     
        session['user_id'] = user.id               
        
        if remember_me:                     
            session.permanent = True     
        return '', 200
        
    except IntegrityError as e:
        db.session.rollback()
        auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 400

    except Exception as e:
        db.session.rollback()
        auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}") 
        return '', 500  
      
    
    
###############################################################################################################
##############################################Forgot Password##################################################
###############################################################################################################

    
    
@bp.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per 30 minutes")
def reset_link():
    
    data = request.get_json()  
    email = (data.get("email") or "").strip()
    
    try:
        valid = validate_email(email)
        email = valid.email  
    except EmailNotValidError as e:
        return jsonify(message="EMAIL_NOT_VALID"), 400
        
    user = User.query.filter_by(email = email).first()
    if user is None:
        return jsonify(message="USER_NOT_FOUND"), 400
    else:
        if not user.is_active:
            return jsonify(message="USER_NOT_ACTIVE"), 400
        else:
            from .celery_tasks import send_password_email
            send_password_email.delay(user.id)
            return '', 201
        
    
###############################################################################################################
##############################################Reset Password###################################################
###############################################################################################################
    
    
def get_serializer2():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY2'])
    
          
def verify_token2(token, expiration=3600):
    serializer = get_serializer2()
    try:
        data = serializer.loads(token, max_age=expiration)
        email = data['email']
        ts = data['ts']
    except (BadSignature, SignatureExpired, KeyError) as e:
        return None

    user = User.query.filter_by(email=email).first()
    if not user or not user.reset_token_issued_at:
        return None

    
    if abs(user.reset_token_issued_at.timestamp() - ts) > 1:
        return None  
    return user
    
    
@bp.route('/reset-password/<token>', methods=('GET', 'POST'))
@limiter.limit("5 per 30 minutes")
def reset_password(token):
    if request.method == "GET":
        user = verify_token2(token)
        if user is None:
            return '', 400
        return '', 200
        
    elif request.method == "POST":
        user = verify_token2(token)
        if user is None:
            return '', 400
        data = request.get_json()
        password1 = data.get("password1")
        password2 = data.get("password2")
        if not is_valid_password(password1) or not is_valid_password(password2):
            return jsonify(message="PASSWORD_NOT_VALID"), 400
        if password1 != password2:
            return jsonify(message="PASSWORD_DONT_CORRESPOND"), 400
        try:
            user.password = generate_password_hash(password1, method='pbkdf2:sha256')  
            user.reset_token_issued_at = datetime.utcnow()             
            db.session.commit()
            return '', 200
        except IntegrityError as e:
            db.session.rollback()
            auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 400
        
        except Exception as e:
            db.session.rollback()
            auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 500  
    
    
        
###############################################################################################################
############################################Before App Request#################################################
###############################################################################################################
    

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = User.query.filter_by(id = user_id).first()
    
      
###############################################################################################################
########################################API to expose the logged in user#######################################
###############################################################################################################
    

@bp.route('/user', methods=['GET'])
def get_current_user():

    try: 
        if g.user is None:
            return jsonify({"user": None}), 401

        data = {
            "id": g.user.id,
            "username": g.user.username,
            "email": g.user.email,
            "name": g.user.name,
            "surname": g.user.surname,
            "age": g.user.age,
            "bio": g.user.bio,
            "sex": g.user.sex,
            "lang": g.user.lang,
            "is_premium": g.user.is_premium,
        }
    except Exception as e:
        auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}") 
        return '', 400
    
    return jsonify(data), 200
    
    
    
    
###############################################################################################################
####################################Require Authentication in Other Routes#####################################
###############################################################################################################


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return '', 400

        return view(**kwargs)

    return wrapped_view
    
        
    
###############################################################################################################
##################################################Log Out######################################################
###############################################################################################################


@bp.route('/logout', methods=['POST'])
@limiter.limit("5 per 10 minutes")
@login_required
def logout():
    try:
        session.clear()
        resp = jsonify(message="Logout succesful!")
        resp.set_cookie('session', '', expires=0)
        return resp, 200
    except Exception as e:
        auth_logger.error(f"[{datetime.utcnow()}] | USER: {getattr(getattr(g, 'user', None), 'username', 'anonymous')} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}") 
        return '', 400
    


###############################################################################################################
###############################################API to debus sessions###########################################
###############################################################################################################


@bp.route('/debug-session', methods=['GET'])
def debug_session():
    return jsonify(dict(session)), 200
    
    
    
