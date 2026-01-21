from server import create_app
from server.celery_utils import make_celery, celery
import server.celery_tasks  


app = create_app()
make_celery(app)  

__all__ = ("celery",)

