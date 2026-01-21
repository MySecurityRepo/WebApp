import os
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from redis import Redis
from flask import current_app

mail = Mail()
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://:r3d1zs0ck37P4sS^@localhost:6379/1")
csrf = CSRFProtect()
db = SQLAlchemy()
socketio = SocketIO(async_mode="gevent") 


r = None
def init_redis(app):
    global r
    url = app.config.get('REDIS_URL')
    if not url:
        raise RuntimeError("REDIS_URL missing in app.config")
    client = Redis.from_url(url)
    client.ping()
    app.extensions['redis_client'] = client
    r = client  


#def get_redis():
    #client = current_app.extensions.get('redis_client')
    #if client is None:
    #    url = current_app.config['REDIS_URL']
    #    client = Redis.from_url(url)
    #    current_app.extensions['redis_client'] = client
    #return client
