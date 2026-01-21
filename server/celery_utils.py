###############################################################################################################
################################################Set Up Celery##################################################
###############################################################################################################



from celery import Celery

celery = Celery(__name__)  # Just define it here

def make_celery(app):
    
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config.get("CELERY_RESULT_BACKEND"),
        timezone=app.config.get("CELERY_TIMEZONE"),
        enable_utc=app.config.get("CELERY_ENABLE_UTC"),
        broker_connection_retry = True,  
        broker_connection_retry_on_startup = True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        broker_transport_options={"visibility_timeout": 3600},
        task_routes={
            "server.celery_tasks.maintenance.*": {"queue": "maintenance"},
            "server.celery_tasks.emails.*": {"queue": "emails"},
            "server.celery_tasks.moderation.*": {"queue": "moderation"},
        },
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
