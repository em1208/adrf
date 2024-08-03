from django.core.handlers.asgi import ASGIRequest
from django.test import TestCase, override_settings
from django.urls import path, reverse
from rest_framework import status
from rest_framework.response import Response

from adrf.decorators import api_view
from adrf.test import AsyncAPIClient, AsyncAPIRequestFactory


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


urlpatterns = [
    path(r"basic_async_view/", basic_async_view),
    path(r"basic_view/", basic_view),
]
factory = AsyncAPIRequestFactory()


class FactoryOnBasicViewTest(TestCase):
    def setUp(self):
        self.view = basic_view

    def test_is_it_asgi(self):
        request = factory.request(path="/", method="GET")
        assert isinstance(
            request, ASGIRequest
        ), f'Type of request is "{type(request).__name__}"'

    def test_get_succeeds(self):
        request = factory.get("/")
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


class FactoryOnAsyncViewTest(TestCase):
    def setUp(self):
        self.factory = AsyncAPIRequestFactory()
        self.view = basic_async_view

    async def test_get_succeeds(self):
        request = factory.get("/")
        response = await self.view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    async def test_post_succeeds(self):
        request = factory.post("/", {"test": "foo"})
        response = await self.view(request)
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_patch_succeeds(self):
        request = factory.patch("/", {"test": "foo"})
        response = await self.view(request)
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_put_succeeds(self):
        request = factory.put("/", {"test": "foo"})
        response = await self.view(request)
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_options_succeeds(self):
        request = factory.options("/")
        response = await self.view(request)
        assert response.status_code == status.HTTP_200_OK


@override_settings(ROOT_URLCONF=__name__)
class ClientOnBasicViewTest(TestCase):
    def setUp(self):
        self.client = AsyncAPIClient()
        self.url = reverse(basic_view)

    async def test_get_succeeds(self):
        response = await self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    async def test_post_succeeds(self):
        response = await self.client.post(self.url, {"test": "foo"})
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_patch_succeeds(self):
        response = await self.client.patch(self.url, {"test": "foo"})
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_put_succeeds(self):
        response = await self.client.put(self.url, {"test": "foo"})
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_options_succeeds(self):
        response = await self.client.options(self.url)
        assert response.status_code == status.HTTP_200_OK


@override_settings(ROOT_URLCONF=__name__)
class ClientOnBasicAsyncViewTest(TestCase):
    def setUp(self):
        self.client = AsyncAPIClient()
        self.url = reverse(basic_async_view)

    async def test_get_succeeds(self):
        response = await self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"method": "GET"}

    async def test_post_succeeds(self):
        response = await self.client.post(self.url, {"test": "foo"})
        expected = {"method": "POST", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_patch_succeeds(self):
        response = await self.client.patch(self.url, {"test": "foo"})
        expected = {"method": "PATCH", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_put_succeeds(self):
        response = await self.client.put(self.url, {"test": "foo"})
        expected = {"method": "PUT", "data": {"test": ["foo"]}}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    async def test_options_succeeds(self):
        response = await self.client.options(self.url)
        assert response.status_code == status.HTTP_200_OK
