import logging
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from pos.models import PointOfSaleToken

logger = logging.getLogger(__name__)
User = get_user_model()


class POSTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
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
            pos_token = PointOfSaleToken.objects.select_related("pos").get(token=token, pos__is_active=True)
        except PointOfSaleToken.DoesNotExist:
            logger.warning("Invalid POS token attempted authentication")
            raise AuthenticationFailed("Токен недействителен")

        pos_user, _ = User.objects.get_or_create(
            username="pos_system",
            defaults={"is_active": True, "is_staff": False, "is_superuser": False},
        )

        logger.info(
            "POS authenticated",
            extra={"pos_id": pos_token.pos.id, "pos_name": pos_token.pos.name}
        )

        pos_user.pos = pos_token.pos
        return (pos_user, None)
