import copy

from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from adrf.decorators import api_view
from adrf.views import APIView

factory = APIRequestFactory()


JSON_ERROR = "JSON parse error - Expecting value:"


def sanitise_json_error(error_dict):
    """
    Exact contents of JSON error messages depend on the installed version
    of json.
    """
    ret = copy.copy(error_dict)
    chop = len(JSON_ERROR)
    ret["detail"] = ret["detail"][:chop]
    return ret


class BasicView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"method": "GET"})

    def post(self, request, *args, **kwargs):
        return Response({"method": "POST", "data": request.data})

    def put(self, request, *args, **kwargs):
        return Response({"method": "PUT", "data": request.data})

    def patch(self, request, *args, **kwargs):
        return Response({"method": "PATCH", "data": request.data})


class BasicAsyncView(APIView):
    async def get(self, request, *args, **kwargs):
        return Response({"method": "GET"})

    async def post(self, request, *args, **kwargs):
        return Response({"method": "POST", "data": request.data})

    async def put(self, request, *args, **kwargs):
        return Response({"method": "PUT", "data": request.data})

    async def patch(self, request, *args, **kwargs):
        return Response({"method": "PATCH", "data": request.data})


@api_view(["GET", "POST", "PUT", "PATCH"])
def basic_view(request):
    if request.method == "GET":
        return Response({"method": "GET"})
    elif request.method == "POST":
        return Response({"method": "POST", "data": request.data})
    elif request.method == "PUT":
        return Response({"method": "PUT", "data": request.data})
    elif request.method == "PATCH":
        return Response({"method": "PATCH", "data": request.data})


@api_view(["GET", "POST", "PUT", "PATCH"])
async def basic_async_view(request):
    if request.method == "GET":
        return Response({"method": "GET"})
    elif request.method == "POST":
        return Response({"method": "POST", "data": request.data})
    elif request.method == "PUT":
        return Response({"method": "PUT", "data": request.data})
    elif request.method == "PATCH":
        return Response({"method": "PATCH", "data": request.data})


class ClassBasedViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = BasicView.as_view()

    def test_get_succeeds(self):
        request = factory.get("/")
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user("user", "user@example.com", "password")
        request = factory.get("/")
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_post_succeeds(self):
        request = factory.post("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_patch_succeeds(self):
        request = factory.patch("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_put_succeeds(self):
        request = factory.put("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options("/")
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post("/", "f00bar", content_type="application/json")
        response = self.view(request)
        expected = {"detail": JSON_ERROR}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected


class FunctionBasedViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = basic_view

    def test_get_succeeds(self):
        request = factory.get("/")
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user("user", "user@example.com", "password")
        request = factory.get("/")
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_post_succeeds(self):
        request = factory.post("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_patch_succeeds(self):
        request = factory.patch("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_put_succeeds(self):
        request = factory.put("/", {"test": "foo"})
        response = self.view(request)
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options("/")
        response = self.view(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post("/", "f00bar", content_type="application/json")
        response = self.view(request)
        expected = {"detail": JSON_ERROR}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected


class ClassBasedAsyncViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = BasicAsyncView.as_view()

    def test_get_succeeds(self):
        request = factory.get("/")
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user("user", "user@example.com", "password")
        request = factory.get("/")
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_post_succeeds(self):
        request = factory.post("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_patch_succeeds(self):
        request = factory.patch("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_put_succeeds(self):
        request = factory.put("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options("/")
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post("/", "f00bar", content_type="application/json")
        response = async_to_sync(self.view)(request)
        expected = {"detail": JSON_ERROR}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected


class FunctionBasedAsyncViewIntegrationTests(TestCase):
    def setUp(self):
        self.view = basic_async_view

    def test_get_succeeds(self):
        request = factory.get("/")
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user("user", "user@example.com", "password")
        request = factory.get("/")
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    def test_post_succeeds(self):
        request = factory.post("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_patch_succeeds(self):
        request = factory.patch("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_put_succeeds(self):
        request = factory.put("/", {"test": "foo"})
        response = async_to_sync(self.view)(request)
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options("/")
        response = async_to_sync(self.view)(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post("/", "f00bar", content_type="application/json")
        response = async_to_sync(self.view)(request)
        expected = {"detail": JSON_ERROR}
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected
