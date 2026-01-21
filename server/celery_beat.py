from server import create_app
from server.celery_utils import make_celery, celery
import server.celery_tasks

app = create_app()
make_celery(app)

from celery.schedules import crontab
beat = {}
for name, entry in app.config.get("CELERY_BEAT_SCHEDULE", {}).items():
    sched = entry["schedule"]
    if isinstance(sched, dict) and sched.get("type") == "crontab":
        beat[name] = {
            "task": entry["task"],
            "schedule": crontab(
                minute=sched.get("minute", 0),
                hour=sched.get("hour", "*"),
                day_of_week=sched.get("day_of_week", "*"),
                day_of_month=sched.get("day_of_month", "*"),
                month_of_year=sched.get("month_of_year", "*"),
            ),
        }
        
celery.conf.beat_schedule = beat

__all__ = ("celery",)


#celery -A server.celery_beat:celery beat --loglevel=info
