import logging
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from pos.models import PointOfSaleToken

logger = logging.getLogger(__name__)


class POSTokenUser(User):
    class Meta:
        proxy = True

    def __init__(self, pos, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos = pos
        self.pk = -1
        self.username = f"pos_{pos.id}"
        self.is_staff = False
        self.is_superuser = False
        self.is_active = True


class POSUserWrapper:
    def __init__(self, pos):
        self.pos = pos

    @property
    def is_authenticated(self):
        return True


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

        logger.info("POS authenticated", extra={"pos_id": pos_token.pos.id, "pos_name": pos_token.pos.name})
        return (POSTokenUser(pos_token.pos), None)
