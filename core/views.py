import logging
import redis
from django.db.utils import OperationalError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.utils.health import check_db, check_redis, check_celery

logger = logging.getLogger(__name__)


@api_view(['GET'])
def health(request):
    status = {"db": True, "redis": True, "celery": True, "status": "ok"}

    try:
        check_db()
    except OperationalError as e:
        status["db"] = False
        status["status"] = "error"
        logger.error("DB health check failed", exc_info=e)

    try:
        check_redis()
    except redis.exceptions.RedisError as e:
        status["redis"] = False
        status["status"] = "error"
        logger.error("Redis health check failed", exc_info=e)

    try:
        if not check_celery():
            status["celery"] = False
            status["status"] = "error"
            logger.error("Celery health check failed: no workers responding")
    except Exception as e:
        status["celery"] = False
        status["status"] = "error"
        logger.error("Celery health check failed", exc_info=e)

    return Response(status)
