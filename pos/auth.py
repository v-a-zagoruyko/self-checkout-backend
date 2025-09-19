import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import PointOfSaleToken

logger = logging.getLogger(__name__)

class POSTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning("Authorization header missing")
            return None

        try:
            prefix, token = auth_header.split(" ")
        except ValueError:
            logger.warning("Authorization header has invalid format")
            raise AuthenticationFailed("Неправильный формат токена")

        if prefix.lower() != "token":
            logger.warning("Authorization header has invalid prefix")
            raise AuthenticationFailed("Неправильный тип токена")

        try:
            pos_token = PointOfSaleToken.objects.select_related("pos").get(key=token)
        except PointOfSaleToken.DoesNotExist:
            logger.warning("Invalid POS token attempted authentication")
            raise AuthenticationFailed("Токен недействителен")

        logger.info("POS authenticated", extra={"pos_id": pos_token.pos.id, "pos_name": pos_token.pos.name})
        return (pos_token.pos, None)
