import unittest.mock

from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.permissions import BasePermission
from rest_framework.test import APIRequestFactory

from adrf.permissions import AsyncBasePermission
from adrf.views import APIView

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
    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_pure_async_logical_and_permission(
        self, mock_has_perm_a, mock_has_perm_b
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncPermission & AsyncRejectPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_has_perm_a.assert_awaited()
        mock_has_perm_b.assert_awaited()
        self.assertEqual(response.status_code, 403)

    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_pure_async_logical_or_permission(
        self, mock_has_perm_a, mock_has_perm_b
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncRejectPermission | AsyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_has_perm_a.assert_awaited()
        mock_has_perm_b.assert_awaited()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_pure_async_logical_neg_permission(self, mock_has_perm):
        request = factory.get("/view/async/allow/")
        negated_permission = ~AsyncRejectPermission

        response = await MockView.as_view(permission_classes=(negated_permission,))(
            request
        )

        mock_has_perm.assert_awaited()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    async def test_mixed_logical_and_permission(
        self, mock_has_perm_async, mock_has_perm_sync
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = SyncPermission & AsyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_has_perm_async.assert_awaited()
        mock_has_perm_sync.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_mixed_logical_or_permission(
        self, mock_has_perm_async, mock_has_perm_sync
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncRejectPermission | SyncPermission

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_has_perm_async.assert_awaited()
        mock_has_perm_sync.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=False)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_async_first_complex_mixed_permission(
        self, mock_async_reject, mock_async_accept, mock_sync_reject
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = AsyncPermission & (
            SyncPermission | ~AsyncRejectPermission
        )

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_async_reject.assert_awaited()
        mock_async_accept.assert_awaited()
        mock_sync_reject.assert_called()
        self.assertEqual(response.status_code, 200)

    @unittest.mock.patch.object(SyncPermission, "has_permission", return_value=True)
    @unittest.mock.patch.object(AsyncPermission, "has_permission", return_value=False)
    @unittest.mock.patch.object(
        AsyncRejectPermission, "has_permission", return_value=False
    )
    async def test_sync_first_complex_mixed_permission(
        self, mock_async_reject, mock_async_accept, mock_sync_reject
    ):
        request = factory.get("/view/async/allow/")
        combined_permission = SyncPermission & (
            AsyncPermission | ~AsyncRejectPermission
        )

        response = await MockView.as_view(permission_classes=(combined_permission,))(
            request
        )

        mock_async_reject.assert_awaited()
        mock_async_accept.assert_awaited()
        mock_sync_reject.assert_called()
        self.assertEqual(response.status_code, 200)


class AsyncMessagePermission(AsyncBasePermission):
    message = "Async permission denied for a specific reason."
    code = "async_denied"

    async def has_permission(self, request, view):
        return False


class SyncMessagePermission(BasePermission):
    message = "Sync permission denied for a specific reason."
    code = "sync_denied"

    def has_permission(self, request, view):
        return False


class AsyncAllowPermission(AsyncBasePermission):
    message = "This permission allowed the request, so its message must not be used."

    async def has_permission(self, request, view):
        return True


class MessageView(APIView):
    # `permission_denied` short circuits to `NotAuthenticated` when the request
    # carries authenticators but none succeeded, which would mask the message
    # under test.
    authentication_classes = ()

    async def get(self, request):
        return HttpResponse("ok")


@override_settings(ROOT_URLCONF=__name__)
class TestPermissionDeniedMessage(TestCase):
    """The denial message and code are read from the permission that denied."""

    async def test_async_permission_denied_message(self):
        request = factory.get("/view/async/reject/")

        response = await MessageView.as_view(
            permission_classes=(AsyncMessagePermission,)
        )(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], AsyncMessagePermission.message)
        self.assertEqual(response.data["detail"].code, AsyncMessagePermission.code)

    async def test_sync_permission_denied_message(self):
        request = factory.get("/view/sync/reject/")

        response = await MessageView.as_view(
            permission_classes=(SyncMessagePermission,)
        )(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], SyncMessagePermission.message)
        self.assertEqual(response.data["detail"].code, SyncMessagePermission.code)

    async def test_async_permission_denied_message_of_the_denying_permission(self):
        """The message must come from the permission that actually returned False."""
        request = factory.get("/view/async/reject/")

        response = await MessageView.as_view(
            permission_classes=(AsyncAllowPermission, AsyncMessagePermission)
        )(request)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], AsyncMessagePermission.message)
