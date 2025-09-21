import os
import redis
from django.conf import settings
from django.db import connections
from celery import Celery

app = Celery("core")
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

def check_db():
    connections["default"].cursor()
    return True

def check_redis():
    r = redis.Redis.from_url(REDIS_URL)
    r.ping()
    return True

def check_celery():
    insp = app.control.inspect(timeout=1)
    return bool(insp.ping())
