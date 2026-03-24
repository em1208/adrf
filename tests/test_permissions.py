import unittest.mock

from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.permissions import BasePermission
from rest_framework.test import APIRequestFactory

from adrf.views import APIView
from adrf.permissions import AsyncBasePermission

factory = APIRequestFactory()


class AsyncPermission(AsyncBasePermission):
    async def has_permission(self, request, view):
        path = request.path_info.lstrip("/")

        if path != "view/async/allow/":
            return False

        return True

    async def has_object_permission(self, request, view, obj):
        return True


class AsyncRejectPermission(AsyncBasePermission):
    async def has_permission(self, request, view):
        return False

    async def has_object_permission(self, request, view, obj):
        return False


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


class TestAsyncPermissionLogicOperators(TestCase):
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_pure_async_logical_and_permission(self, mock_has_perm_a, mock_has_perm_b):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncPermission & AsyncRejectPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_has_perm_a.assert_awaited()
        mock_has_perm_b.assert_awaited()
        self.assertEqual(response.status_code, 403)

    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_pure_async_logical_or_permission(self, mock_has_perm_a, mock_has_perm_b):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncRejectPermission | AsyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_has_perm_a.assert_awaited()
        mock_has_perm_b.assert_awaited()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_pure_async_logical_neg_permission(self, mock_has_perm):
        request = factory.get("/view/async/allow/")
        negated_permission = ~AsyncRejectPermission

        response = await MockView.as_view(permission_classes=(negated_permission,))(request)

        mock_has_perm.assert_awaited()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    async def test_mixed_logical_and_permission(self, mock_has_perm_async, mock_has_perm_sync):
        request = factory.get("/view/async/allow/")
        combined_permission = SyncPermission & AsyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_has_perm_async.assert_awaited()
        mock_has_perm_sync.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_mixed_logical_or_permission(self, mock_has_perm_async, mock_has_perm_sync):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncRejectPermission | SyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_has_perm_async.assert_awaited()
        mock_has_perm_sync.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=False)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_async_first_complex_mixed_permission(self, mock_async_reject, mock_async_accept, mock_sync_reject):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncPermission & (SyncPermission | ~AsyncRejectPermission)

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_async_reject.assert_awaited()
        mock_async_accept.assert_awaited()
        mock_sync_reject.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=False)
    @unittest.mock.patch.object(AsyncRejectPermission, "has_permission", return_value=False)
    async def test_sync_first_complex_mixed_permission(self, mock_async_reject, mock_async_accept, mock_sync_reject):
        request = factory.get("/view/async/allow/")
        combined_permission = SyncPermission & (AsyncPermission | ~AsyncRejectPermission)

        response = await MockView.as_view(permission_classes=(combined_permission,))(request)

        mock_async_reject.assert_awaited()
        mock_async_accept.assert_awaited()
        mock_sync_reject.assert_called()
        self.assertEqual(response.status_code, 200)
