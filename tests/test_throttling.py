from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import BaseThrottle

from adrf.views import APIView

factory = APIRequestFactory()


class AsyncThrottle(BaseThrottle):
    async def allow_request(self, request, view):
        if not hasattr(self.__class__, "called"):
            self.__class__.called = True
            return True

        return False

    def wait(self):
        return 3


class MockView(APIView):
    throttle_classes = [AsyncThrottle]

    async def get(self, request):
        return HttpResponse()


@override_settings(ROOT_URLCONF=__name__)
class TestAsyncThrottling(TestCase):
    async def test_throttle(self):
        """
        Ensure throttling is applied correctly.
        """
        request = factory.get("/")

        self.assertFalse(hasattr(MockView.throttle_classes[0], "called"))

        response = await MockView.as_view()(request)
        self.assertFalse("Retry-After" in response)

        self.assertTrue(MockView.throttle_classes[0].called)

        response = await MockView.as_view()(request)
        self.assertTrue("Retry-After" in response)
        self.assertEqual(response["Retry-After"], "3")
