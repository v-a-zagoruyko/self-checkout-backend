import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch
from .factories import PointOfSaleTokenFactory

@pytest.fixture(autouse=True)
def disable_rollbar():
    with patch("rollbar.report_message"), patch("rollbar.report_exc_info"):
        yield

@pytest.fixture
def api_client():
	return APIClient()

@pytest.fixture
def auth_client(db):
    pos_token = PointOfSaleTokenFactory()
    user = User.objects.create_user(username="dummy_user")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {pos_token.token}")
    client.handler._force_user = user
    return client
