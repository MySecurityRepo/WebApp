import mimetypes, smtplib, logging, shutil, tempfile, fitz, subprocess, os, json, traceback, json, concurrent.futures
from flask import current_app, render_template
from .blog import upload_logger, blog_logger
from .models import User, FileUpload, MessageAttachment, PostAttachment, CommentAttachment, BioAttachment, Comment, Post, ThreadUser,Thread, Message
from .extensions import db
from datetime import datetime, timezone, timedelta
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_, exists, select, func, delete
from pypdf import PdfReader
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from .extensions import mail, limiter
from botocore.exceptions import ClientError



# Logger for manteinance
manteinance_logger = logging.getLogger("manteinance")
manteinance_logger.setLevel(logging.ERROR)
manteinance_handler = logging.handlers.WatchedFileHandler("/home/webserver/logs/manteinance_exceptions.log")
manteinance_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
if not manteinance_logger.hasHandlers():
    manteinance_logger.addHandler(manteinance_handler)


###############################################################################################################
############################################Utility Functions##################################################
###############################################################################################################


def validate_video(path, username, ip, filename):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        duration_str = result.stdout.decode().strip()
        duration = float(duration_str)
        if duration <= 0:
            return False
            
        
        video_check = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v',
             '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        video_streams = video_check.stdout.decode().strip().split('\n')
        
        
        audio_check = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a',
             '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        audio_streams = audio_check.stdout.decode().strip().split('\n')
          
        if not any(s.strip().lower() == 'video' for s in video_streams) and not any(s.strip().lower() == 'audio' for s in audio_streams):
            return False
        return True
        
    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
        return False



def is_valid_pdf(path, username, ip, filename):
    try:
        reader = PdfReader(path)
        return reader.pages and len(reader.pages) > 0
    except Exception:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
        return False


def contains_embedded_files(path, username, ip, filename):
    try:
        doc = fitz.open(path)
        
        if doc.embfile_count() > 0:
            return True
            
        try:
            catalog = doc.pdf_catalog()
            if isinstance(catalog, dict) and "OpenAction" in catalog:
                return True
                
        except Exception as e:
            upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
            return True
                        
        for i, page in enumerate(doc):
            links = page.get_links()
            for link in links:
                if 'javascript' in str(link).lower():
                    return True             
        return False
        
    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")   
        return True 


        
def strip_pdf_metadata(path, username, ip, filename):
    try:
        doc = fitz.open(path)
        doc.set_metadata({})
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
        
        doc.save(temp_path, garbage=4, deflate=True)
        doc.close()
        shutil.move(temp_path, path)
        
    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
        raise 



def reject_file(path, username, ip, filename):
    try:
        
        rows_updated = FileUpload.query.filter_by(path=path).update({"status": "rejected"})
        if rows_updated:
            db.session.commit()
        else:
            pass 
                                                                  
    except IntegrityError as ef:
        db.session.rollback()
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
                        
    except Exception as e:
        db.session.rollback()
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")   
                
    return "rejected"




###############################################################################################################
############################################Celery Validation##################################################
###############################################################################################################

from server.celery_utils import celery 


@celery.task(name='server.celery_tasks.moderation.moderate_file_async')
def moderate_file_async(path, mime, username, ip, filename, is_animated=None):
    try:
             
        if mime.startswith("image/") and is_animated is None:
            from .moderation.image import moderate_image
            result = moderate_image(path=path, username=username, ip=ip, filename=filename)
            if isinstance(result, list) and len(result) == 1:
                result = result[0]
            if not result:
                reject_file(path, username, ip, filename)
                return "rejected"
        
        elif mime.startswith("image/") and is_animated is not None:
            from .moderation.gif import moderate_gif
            if not moderate_gif(path=path, username=username, ip=ip, filename=filename):
                reject_file(path, username, ip, filename)
                return "rejected"
                
                                        
        elif mime.startswith("video/"):
            if not validate_video(path, username, ip, filename): 
                reject_file(path, username, ip, filename)
                return "rejected"
                               
            from .moderation.video import moderate_video
            if not moderate_video(path, username, ip, filename):
                reject_file(path, username, ip, filename)
                return "rejected"      
                     
        elif mime == "application/pdf":
            if not is_valid_pdf(path, username, ip, filename) or contains_embedded_files(path, username, ip, filename):
                reject_file(path, username, ip, filename)
                return "rejected"
            
            from .moderation.pdf import moderate_pdf
            if not moderate_pdf(path, username, ip, filename):
                reject_file(path, username, ip, filename)
                return "rejected"
                
            strip_pdf_metadata(path, username, ip, filename)
        
        try:
            rows_updated = FileUpload.query.filter_by(path=path).update({"status": "approved"})
            if rows_updated:
                db.session.commit()
            else:
                pass
        except IntegrityError as ef:
            db.session.rollback()
            upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")   
            
        return "approved"

    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
        return "error"
        
        
###############################################################################################################
############################################Celery Sending Mail################################################
###############################################################################################################

SUPPORTED_LANGS = ['en','it','fr','es','de','pt','ru','zh','ja','ar','hi']


def _lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"
    

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])  
                  
                                                              
def generate_token(user):
    serializer = get_serializer()                            
    payload = {                                               
        'email': user.email,                                  
        'ts': user.reset_token_issued_at.timestamp()
    }
    return serializer.dumps(payload)                          
                         
                                                                      
@celery.task(name='server.celery_tasks.emails.send_verification_email', autoretry_for=(ConnectionError, TimeoutError, smtplib.SMTPException), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                
def send_verification_email(user_id):

    try:
        user = db.session.query(User).filter(User.id == user_id).first()
        if not user:
            return
    
        title = {"en":"Confirm Your Email","it":"Conferma la tua email","fr":"Vérifier ton adresse e-mail","es":"Verificar tu correo electrónico","de":"E-Mail bestätigen", "pt":"Confirmar seu e-mail","ru":"Подтвердить адрес электронной почты","zh":"确认您的邮箱","ja":"メールアドレスを確認する", "hi":"अपना ईमेल सत्यापित करें",}

        token = generate_token(user)
        link = f"{current_app.config['FRONTEND_URL']}/confirmation?token={token}"
        msg = Message(title[_lang(user.lang)], recipients=[user.email])
        msg.html = render_template(f"emails/verify_email_{user.lang}.html", user=user, link=link)
        msg.body = render_template(f"emails/verify_email_{user.lang}.txt", user=user, link=link)
        mail.send(msg)
    
    except Exception as e:
        db.session.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: SEND_VERIFICATION_EMAIL | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500




def get_serializer2():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY2'])
                                                                   
                                                                                                                                
def generate_token2(user):
    serializer = get_serializer2()
    payload = {
        'email': user.email,
        'ts': user.reset_token_issued_at.timestamp()
    }
    return serializer.dumps(payload)
                    
                                          
                                                               
@celery.task(name='server.celery_tasks.emails.send_password_email', autoretry_for=(ConnectionError, TimeoutError, smtplib.SMTPException), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                                                                    
def send_password_email(user_id):
    
    try:
        user = db.session.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        title = {"en":"Reset Your Password","it":"Ripristina la tua password","fr":"Réinitialiser ton mot de passe","es":"Restablecer tu contraseña","de":"Passwort zurücksetzen", "pt":"Redefinir sua senha","ru":"Сбросить пароль","zh":"重置您的密码","ja":"パスワードをリセットする", "hi":"अपना पासवर्ड रीसेट करें",}
        
        token = generate_token2(user)
        link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
        msg = Message(title[_lang(user.lang)], recipients=[user.email])
        msg.html = render_template(f"emails/reset_password_{user.lang}.html", user=user, link=link)
        msg.body = render_template(f"emails/reset_password_{user.lang}.txt", user=user, link=link)
        mail.send(msg)
    except Exception as e:
        db.session.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: SEND_PASSWORD_EMAIL | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500



def get_serializer3():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY3'])  
 
                                                                        
def generate_token3(user):
    serializer = get_serializer3()                             
    payload = {                                               
        'email': user.email,                                  
        'ts': user.reset_token_issued_at.timestamp()
    }
    return serializer.dumps(payload)                          
    
                                                              
@celery.task(name='server.celery_tasks.emails.send_delete_account_email', autoretry_for=(ConnectionError, TimeoutError, smtplib.SMTPException), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                             
def send_delete_account_email(user_id):
    
    try:
        user = db.session.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        title = {"en":"Delete Your Account","it":"Elimina il tuo Account","fr":"Supprimer ton compte","es":"Eliminar tu cuenta","de":"Konto löschen", "pt":"Excluir sua conta","ru":"Удалить аккаунт","zh":"删除您的账户","ja":"アカウントを削除する", "hi":"अपना खाता हटाएं",}

        token = generate_token3(user)
        link = f"{current_app.config['FRONTEND_URL']}/delete-confirmation?token={token}"
        msg = Message(title[_lang(user.lang)], recipients=[user.email])
        msg.html = render_template(f"emails/delete_account_{user.lang}.html", user=user, link=link)
        msg.body = render_template(f"emails/delete_account_{user.lang}.txt", user=user, link=link)
        mail.send(msg)
    except Exception as e:
        db.session.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: SEND_DELETE_ACCOUNT_EMAIL | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500
    

###############################################################################################################
############################################Celery Backing Up to Wasabi########################################
###############################################################################################################

BASE_PATH = "/var/www/"


def _basename(p: str) -> str:
    return os.path.basename(p.rstrip("/"))


def _abs_from_variant_path(rel: str) -> str:
    rel = rel.lstrip("/\\")
    if rel.startswith("static/"):
        rel = rel[len("static/"):]
    return os.path.join(BASE_PATH, rel)


def _abs_from_main_path(abs_path: str) -> str:
    return abs_path


def _gather_files(row):

    files = []
    variants_out = {}

    if row.variants:
        vdict = row.variants if isinstance(row.variants, dict) else json.loads(row.variants)
        if isinstance(vdict, dict) and vdict:
            for size, rel in vdict.items():
                abs_local = _abs_from_variant_path(rel)
                fname = _basename(rel)
                files.append((abs_local, fname))
                variants_out[size] = fname
            return files, variants_out

    if row.path:
        abs_local = _abs_from_main_path(row.path)
        fname = _basename(row.path)
        files.append((abs_local, fname))
        return files, variants_out

    return [], variants_out


def _remote_key(fname: str, WASABI_PREFIX) -> str:
    return f"{WASABI_PREFIX}/{fname}" if WASABI_PREFIX else fname


@celery.task(name='server.celery_tasks.maintenance.backup_to_wasabi', autoretry_for=(ConnectionError, TimeoutError, ClientError), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                             
def backup_to_wasabi(limit: int = 1000):
    
    try: 
        import boto3
        from boto3.s3.transfer import TransferConfig
        
        WASABI_ENDPOINT = current_app.config['WASABI_ENDPOINT']
        WASABI_ACCESS_KEY   = current_app.config['WASABI_ACCESS_KEY']
        WASABI_SECRET_KEY   = current_app.config['WASABI_SECRET_KEY']
        WASABI_REGION   = current_app.config['WASABI_REGION']
        WASABI_BUCKET   = current_app.config['WASABI_BUCKET']
        WASABI_PREFIX   = current_app.config['WASABI_PREFIX']
    
        TX_CFG = TransferConfig(multipart_threshold=8 * 1024 * 1024, multipart_chunksize=16 * 1024 * 1024, max_concurrency=8, use_threads=True,)    
        s3 = boto3.client("s3", endpoint_url=WASABI_ENDPOINT, aws_access_key_id=WASABI_ACCESS_KEY, aws_secret_access_key=WASABI_SECRET_KEY, region_name=WASABI_REGION,)
    
        q = db.session.query(FileUpload).options(load_only(FileUpload.id, FileUpload.path, FileUpload.w_path, FileUpload.mime, FileUpload.variants, FileUpload.w_variants)).filter(FileUpload.status == "approved",
            and_(FileUpload.w_path == None, FileUpload.w_variants == None)).limit(limit)
    
        uploaded = skipped = 0
    
        for row in q.yield_per(200):
            files, variants_out = _gather_files(row)
        
            if not files:
                skipped += 1
                manteinance_logger.error( f"[{datetime.utcnow()}] | TASK: BACKUP_TO_WASABI | ERROR: 'File Path not found while doing backup'")
                continue
        
            for abs_local, fname in files:
                if not os.path.exists(abs_local):
                    variants_out = {}
                    manteinance_logger.error( f"[{datetime.utcnow()}] | TASK: BACKUP_TO_WASABI | ERROR: 'File missing'")
                    break

                with open(abs_local, "rb") as f:
                    s3.upload_fileobj(f, WASABI_BUCKET, _remote_key(fname, WASABI_PREFIX), Config=TX_CFG)
                uploaded += 1
            
            if variants_out:
                row.w_variants = variants_out
                row.w_path = None
            elif files and os.path.exists(files[0][0]):
                row.w_path = files[0][1]
                row.w_variants = None
            else:
                pass

            db.session.commit()
        print(f"uploaded={uploaded}, skipped={skipped}")
        return
    
    except Exception as e:
        db.session.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: BACKUP_TO_WASABI | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500   



###############################################################################################################
############################################Celery Clearing Uploads############################################
###############################################################################################################


BATCH_SIZE = 500
MAX_WORKERS = 8


def _delete_file(path):
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        manteinance_logger.error(f"[{datetime.utcnow()}] | DELETE FILE LOCAL FILE | PATH: {path} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return False


@celery.task(name='server.celery_tasks.maintenance.cleanup_uploads', autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                             
def cleanup_uploads():
    
    try:
        not_in_bio = ~exists().where(BioAttachment.file_upload_id == FileUpload.id)
        not_in_post = ~exists().where(PostAttachment.file_upload_id == FileUpload.id)
        not_in_comment = ~exists().where(CommentAttachment.file_upload_id == FileUpload.id)
        not_in_msg = ~exists().where(MessageAttachment.file_upload_id == FileUpload.id)
        not_referenced_anywhere = and_(not_in_bio, not_in_post, not_in_comment, not_in_msg)
    
        while True:
            rows = db.session.query(FileUpload.id, FileUpload.path, FileUpload.variants, FileUpload.w_path, FileUpload.w_variants ).filter(or_(FileUpload.user_id.is_(None), FileUpload.status == "rejected", not_referenced_anywhere,)).limit(BATCH_SIZE).all()
            if not rows:
                break
        
            import boto3
            from boto3.s3.transfer import TransferConfig
        
            WASABI_ENDPOINT = current_app.config['WASABI_ENDPOINT']
            WASABI_ACCESS_KEY   = current_app.config['WASABI_ACCESS_KEY']
            WASABI_SECRET_KEY   = current_app.config['WASABI_SECRET_KEY']
            WASABI_REGION   = current_app.config['WASABI_REGION']
            WASABI_BUCKET   = current_app.config['WASABI_BUCKET']
            WASABI_PREFIX   = current_app.config['WASABI_PREFIX']
         
            s3 = boto3.client("s3", endpoint_url=WASABI_ENDPOINT, aws_access_key_id=WASABI_ACCESS_KEY, aws_secret_access_key=WASABI_SECRET_KEY, region_name=WASABI_REGION,)
        
            paths = []
            ids_to_delete = []
            for file_id, path, variants_json, w_path, w_variants in rows:
                ids_to_delete.append(file_id)
                if variants_json:
                    try:
                        for label, variant in variants_json.items():
                            paths.append(_abs_from_variant_path(variant))
                    except Exception as e:
                        paths.append(path)
                else:
                    paths.append(path)
            
                if w_variants:
                    for label, variant in w_variants.items():
                        s3.delete_object(Bucket=WASABI_BUCKET, Key=_remote_key(variant, WASABI_PREFIX))
                elif w_path: 
                    s3.delete_object(Bucket=WASABI_BUCKET, Key=_remote_key(w_path, WASABI_PREFIX))
              
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                ex.map(_delete_file, paths)
        
            db.session.query(FileUpload).filter(FileUpload.id.in_(ids_to_delete)).delete(synchronize_session=False)
            db.session.commit()
            
        return
        
    except Exception as e:
        s.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_UPLOADS | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500 
    
    
    
###############################################################################################################
##########################################Celery Delete Backed up files########################################
###############################################################################################################



@celery.task(name='server.celery_tasks.maintenance.delete_backed_up_files', autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                             
def delete_backed_up_files():
    try:
    
        ten_days_ago = datetime.utcnow() - timedelta(days=3)
        rows = db.session.query(FileUpload.id, FileUpload.filename, FileUpload.w_path, FileUpload.w_variants, FileUpload.is_ondisk).filter(and_(FileUpload.created_at < ten_days_ago, FileUpload.is_ondisk==True, or_(FileUpload.w_path.isnot(None), FileUpload.w_variants.isnot(None)))).all()
    
        from pathlib import Path
        upload_root = Path(current_app.config['UPLOAD_FOLDER'])
        files_to_delete = []
        ids_to_update = []
    
        for fid, filename, w_path, w_variant, ondisk in rows:
            if w_variant:
                for _, variant in w_variant.items():
                    filepath = upload_root / variant
                    files_to_delete.append(filepath)
            elif w_path:
                filepath = upload_root / filename    
                files_to_delete.append(filepath)
        
            ids_to_update.append(fid)
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            ex.map(_delete_file, files_to_delete)
        
        if ids_to_update:
            db.session.query(FileUpload).filter(FileUpload.id.in_(ids_to_update)).update({FileUpload.is_ondisk: False}, synchronize_session=False)
            db.session.commit()
            
        return
            
    except Exception as e:
        s.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: DELETE_BACKED_UP_FILES | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500  
    
                           
                
###############################################################################################################
############################################Celery Deleting Users##############################################
###############################################################################################################       
                
                      
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
            manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            return '', 500

    except Exception as e:
        s.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {e}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return '', 500                



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
                s.rollback()
                manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {str(ef)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 400

            except Exception as e3:
                s.rollback()
                manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {str(e3)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                return '', 500              
                
                
            
  
      
def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)   

BATCH_SIZE_USERS = 200

@celery.task(name='server.celery_tasks.maintenance.cleanup_db', autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})                                                             
def cleanup_db():
    
    s = db.session
    cutoff = utcnow_naive() - timedelta(days=15)

    try:
        threads_with_few_users = (select(ThreadUser.thread_id).group_by(ThreadUser.thread_id).having(func.count(ThreadUser.user_id) < 2))
        s.execute(delete(Thread).where(Thread.id.in_(threads_with_few_users)))
    except Exception as e:
        s.rollback()
        manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        
    while True:
        
        ids = [uid for (uid,) in ( s.query(User.id).filter(User.is_suspended.is_(True), User.is_tobedeleted.is_(True), User.delete_request_date <= cutoff).limit(BATCH_SIZE_USERS).all())]
        if not ids:
            break
        ids_tuple = tuple(ids)
            
        try:       
            s.query(User).filter(User.id.in_(ids_tuple)).delete(synchronize_session=False)   
            s.commit()
            continue
        
        except Exception:            
            s.rollback()
            
        try:
            s.query(ThreadUser).filter(ThreadUser.user_id.in_(ids_tuple)).delete(synchronize_session=False)
            s.query(MessageReaction).filter(MessageReaction.user_id.in_(ids_tuple)).delete(synchronize_session=False)
            s.query(Message).filter(Message.sender_id.in_(ids_tuple)).delete(synchronize_session=False)
            s.query(Comment).filter(Comment.author_id.in_(ids_tuple)).delete(synchronize_session=False)
            s.query(Post).filter(Post.author_id.in_(ids_tuple)).delete(synchronize_session=False)
            s.commit()
                
        except Exception:
            s.rollback()
            
            try:
                s.query(ThreadUser).filter(ThreadUser.user_id.in_(ids_tuple)).delete(synchronize_session=False)
                s.query(MessageReaction).filter(MessageReaction.user_id.in_(ids_tuple)).delete(synchronize_session=False)
                s.query(Message).filter(Message.sender_id.in_(ids_tuple)).delete(synchronize_session=False)
            
                for comment in s.query(Comment).filter(Comment.author_id.in_(ids_tuple)).yield_per(500):
                    delete_comment(comment.id)
                for post in s.query(Post).filter(Post.author_id.in_(ids_tuple)).yield_per(200):
                    delete_post(post.id)
                
                s.commit()
            except Exception as e:
                s.rollback()
                manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
                
        try:
            s.query(User).filter(User.id.in_(ids_tuple)).delete(synchronize_session=False)
            s.commit()
        except Exception as e:
            s.rollback()
            manteinance_logger.error(f"[{datetime.utcnow()}] | TASK: CLEANUP_DB |ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
            continue
                       
    
