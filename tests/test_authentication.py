import faker
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework import permissions, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from adrf.decorators import api_view
from adrf.views import APIView

fake = faker.Faker()

faked_user = User(
    username=fake.name(),
    email=fake.email(),
    password=fake.password(),
    is_staff=True,
    is_superuser=True,
)


factory = APIRequestFactory()


class AsyncAuthentication(BaseAuthentication):
    keyword = "Bearer"

    async def authenticate(self, request):
        auth = request.headers.get("Authorization")
        if not auth:
            return None

        if not auth.startswith(self.keyword):
            return None

        token = auth[len(self.keyword) :].strip()

        if token != "admitme":
            raise AuthenticationFailed("Invalid token")

        return faked_user, None

    def authenticate_header(self, request):
        return self.keyword


class MockView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (AsyncAuthentication,)

    async def get(self, request):
        return HttpResponse({"a": 1, "b": 2, "c": 3})


@api_view(("GET",))
@permission_classes([permissions.IsAuthenticated])
@authentication_classes([AsyncAuthentication])
async def mock_view_func(request):
    return HttpResponse({"a": 1, "b": 2, "c": 3})


@override_settings(ROOT_URLCONF=__name__)
class TestAsyncAuthentication(TestCase):
    async def test_admit_customtoken_class_view(self):
        auth = "Bearer admitme"
        request = factory.get("/view/", HTTP_AUTHORIZATION=auth)
        response = await MockView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(request.user, faked_user)

    async def test_reject_customtoken_class_view(self):
        auth = "Bearer expired"
        request = factory.get("/view/", HTTP_AUTHORIZATION=auth)
        response = await MockView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    async def test_admit_customtoken_func_view(self):
        auth = "Bearer admitme"
        request = factory.get("/view/", HTTP_AUTHORIZATION=auth)
        response = await mock_view_func(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(request.user, faked_user)

    async def test_reject_customtoken_func_view(self):
        auth = "Bearer expired"
        request = factory.get("/view/", HTTP_AUTHORIZATION=auth)
        response = await mock_view_func(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
