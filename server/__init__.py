import os
if os.getenv("USE_GEVENT_PATCH") == "1":
    from gevent import monkey
    monkey.patch_all()
from flask import Flask, request, g
from dotenv import load_dotenv
from .extensions import mail, limiter, csrf, db, socketio, init_redis
from datetime import timedelta
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

load_dotenv()  

def create_app():
    
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)
    app.config.from_mapping(
        SECRET_KEY = os.getenv('SECRET_KEY'),
        SECRET_KEY2 = os.getenv('SECRET_KEY2'),
        SECRET_KEY3 = os.getenv('SECRET_KEY3'),
        SQLALCHEMY_DATABASE_URI = f"mysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAIL_SERVER = os.getenv('MAIL_SERVER'),
        MAIL_PORT = int(os.getenv('MAIL_PORT', 587)),
        MAIL_USE_TLS = True,
        MAIL_USE_SSL = False,
        MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER'),
        MAIL_USERNAME = os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),
        PERMANENT_SESSION_LIFETIME = timedelta(days=2),
        UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER'),
        FRONTEND_URL  = os.getenv('FRONTEND_URL'),
        FRONTEND_URL2  = os.getenv('FRONTEND_URL2'),
        BACKEND_URL  = os.getenv('BACKEND_URL'),
        REDIS_URL=os.getenv('REDIS_URL'),
        CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL'),
        CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND'),
        CELERY_TIMEZONE = "Europe/Rome",
        CELERY_ENABLE_UTC = False,
        LOG_LEVEL = 'DEBUG',
        SESSION_COOKIE_SAMESITE="None",   
        SESSION_COOKIE_SECURE=True,        
        SESSION_COOKIE_HTTPONLY=True,
        WTF_CSRF_METHODS = ["POST","PUT","PATCH","DELETE"],
        WTF_CSRF_TIME_LIMIT = 3600,
        WASABI_ACCESS_KEY = os.getenv('WASABI_ACCESS_KEY'),
        WASABI_SECRET_KEY = os.getenv('WASABI_SECRET_KEY'),
        WASABI_BUCKET = os.getenv('WASABI_BUCKET'),
        WASABI_REGION = os.getenv('WASABI_REGION'),
        WASABI_ENDPOINT = os.getenv('WASABI_ENDPOINT'),
        WASABI_PREFIX = os.getenv('WASABI_PREFIX'),
    )
    
    from server.celery_utils import make_celery
    make_celery(app)
    import server.celery_tasks
        
    from . import models
    db.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    CORS(app, supports_credentials=True, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "X-CSRFToken", "X-Lang", "Authorization"])
    init_redis(app)
    mail.init_app(app)
    socketio.init_app(app, message_queue=app.config['REDIS_URL'], cors_allowed_origins=[app.config['FRONTEND_URL'], app.config['FRONTEND_URL2'], "capacitor://localhost", "http://localhost", "https://localhost"], path="/ws", ping_timeout=200, ping_interval=30, max_http_buffer_size=200*1024)    
    from . import auth, blog, chat
    app.register_blueprint(auth.bp)
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["WTF_CSRF_SSL_STRICT"] = False
    
    app.config["CELERY_BEAT_SCHEDULE"] = {
        "cleanup-uploads-daily": {
            "task": "server.celery_tasks.maintenance.cleanup_uploads",
            "schedule": {"type": "crontab", "hour": 4, "minute": 0},  
        },
        "cleanup-db-daily": {
            "task": "server.celery_tasks.maintenance.cleanup_db",
            "schedule": {"type": "crontab", "hour": 3, "minute": 0},
        },
        "backup-uploads_15": {
            "task": "server.celery_tasks.maintenance.backup_to_wasabi",
            "schedule": {"type": "crontab", "minute":15},
        },
        "backup-uploads_45": {
            "task": "server.celery_tasks.maintenance.backup_to_wasabi",
            "schedule": {"type": "crontab", "minute":45},
        },
        "delete_backed_up_files": {
            "task": "server.celery_tasks.maintenance.delete_backed_up_files",
            "schedule": {"type": "crontab", "hour": 5, "minute":0},
        },
    }
    
    @app.before_request
    def log_request_info():
        app.logger.info("REQ %s %s %s", request.method, request.path, dict(request.args))

    @app.after_request
    def log_response_info(response):
        app.logger.info("RES %s", response.status_code)
        return response

    return app
    
    

