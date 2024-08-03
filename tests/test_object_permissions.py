from asgiref.sync import sync_to_async
from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.permissions import BasePermission
from rest_framework.test import APIRequestFactory

from adrf.views import APIView

factory = APIRequestFactory()


class AsyncObjectPermission(BasePermission):
    async def has_permission(self, request, view):
        return True

    async def has_object_permission(self, request, view, obj):
        if obj != "/async/allow":
            return False
        return True


class SyncObjectPermission(BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if obj != "/sync/allow":
            return False
        return True


class ObjectPermissionTestView(APIView):
    permission_classes = (AsyncObjectPermission,)

    async def get(self, request):
        await sync_to_async(self.check_object_permissions)(request, request.path)
        return HttpResponse("ok")


@override_settings(ROOT_URLCONF=__name__)
class TestAsyncObjectPermission(TestCase):
    async def test_async_object_permission(self):
        request = factory.get("/async/allow")

        response = await ObjectPermissionTestView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    async def test_async_object_permission_reject(self):
        request = factory.get("/async/reject")

        response = await ObjectPermissionTestView.as_view()(request)

        self.assertEqual(response.status_code, 403)


@override_settings(ROOT_URLCONF=__name__)
class TestSyncObjectPermission(TestCase):
    async def test_sync_object_permission(self):
        request = factory.get("/sync/allow")

        response = await ObjectPermissionTestView.as_view(
            permission_classes=(SyncObjectPermission,)
        )(request)

        self.assertEqual(response.status_code, 200)

    async def test_sync_object_permission_reject(self):
        request = factory.get("/sync/reject")

        response = await ObjectPermissionTestView.as_view(
            permission_classes=(SyncObjectPermission,)
        )(request)

        self.assertEqual(response.status_code, 403)
