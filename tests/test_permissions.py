from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.permissions import BasePermission
from rest_framework.test import APIRequestFactory

from adrf.views import APIView

factory = APIRequestFactory()


class AsyncPermission(BasePermission):
    async def has_permission(self, request, view):
        path = request.path_info.lstrip("/")

        if path != "view/async/allow/":
            return False

        return True

    async def has_object_permission(self, request, view, obj):
        return True


class SyncPermission(BasePermission):
    def has_permission(self, request, view):
        path = request.path_info.lstrip("/")

        if path != "view/sync/allow/":
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return True


class MockView(APIView):
    permission_classes = (AsyncPermission,)

    async def get(self, request):
        return HttpResponse({"a": 1, "b": 2, "c": 3})


@override_settings(ROOT_URLCONF=__name__)
class TestAsyncPermission(TestCase):
    async def test_async_permission(self):
        request = factory.get("/view/async/allow/")

        response = await MockView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    async def test_async_permission_reject(self):
        request = factory.get("/view/async/reject/")

        response = await MockView.as_view()(request)

        self.assertEqual(response.status_code, 403)


@override_settings(ROOT_URLCONF=__name__)
class TestSyncPermission(TestCase):
    async def test_sync_permission(self):
        request = factory.get("/view/sync/allow/")

        response = await MockView.as_view(permission_classes=(SyncPermission,))(request)

        self.assertEqual(response.status_code, 200)

    async def test_sync_permission_reject(self):
        request = factory.get("/view/sync/reject/")

        response = await MockView.as_view(permission_classes=(SyncPermission,))(request)

        self.assertEqual(response.status_code, 403)
