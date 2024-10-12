from django.test import Client, TestCase, override_settings
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet as DRFModelViewSet

from adrf.routers import SimpleRouter
from adrf.viewsets import ModelViewSet as AsyncModelViewSet


class SyncViewSet(DRFModelViewSet):
    def list(self, request):
        return Response({"method": "GET", "async": False})

    def create(self, request):
        return Response({"method": "POST", "data": request.data, "async": False})

    def retrieve(self, request, pk):
        return Response({"method": "GET", "data": {"pk": pk}, "async": False})

    def update(self, request, pk):
        return Response({"method": "PUT", "data": request.data, "async": False})

    def partial_update(self, request, pk):
        return Response({"method": "PATCH", "data": request.data, "async": False})

    def destroy(self, request, pk):
        return Response({"method": "DELETE", "async": False})


class AsyncViewSet(AsyncModelViewSet):
    async def alist(self, request):
        return Response({"method": "GET", "async": True})

    async def acreate(self, request):
        return Response({"method": "POST", "data": request.data, "async": True})

    async def aretrieve(self, request, pk):
        return Response({"method": "GET", "data": {"pk": pk}, "async": True})

    async def aupdate(self, request, pk):
        return Response({"method": "PUT", "data": request.data, "async": True})

    async def partial_aupdate(self, request, pk):
        return Response({"method": "PATCH", "data": request.data, "async": True})

    async def adestroy(self, request, pk):
        return Response({"method": "DELETE", "async": True})


router = SimpleRouter()
router.register("sync", SyncViewSet, basename="sync")
router.register("async", AsyncViewSet, basename="async")
urlpatterns = router.urls


@override_settings(ROOT_URLCONF="tests.test_routers")
class _RouterIntegrationTests(TestCase):
    use_async = None
    __test__ = False

    def setUp(self):
        self.client = Client()
        self.url = "/" + ("async" if self.use_async else "sync") + "/"
        self.detail_url = self.url + "1/"

    def test_list(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert resp.data == {"method": "GET", "async": self.use_async}

    def test_create(self):
        resp = self.client.post(
            self.url, {"foo": "bar"}, content_type="application/json"
        )
        assert resp.status_code == 200
        assert resp.data == {
            "method": "POST",
            "data": {"foo": "bar"},
            "async": self.use_async,
        }

    def test_retrieve(self):
        resp = self.client.get(self.detail_url)
        assert resp.status_code == 200
        assert resp.data == {
            "method": "GET",
            "data": {"pk": "1"},
            "async": self.use_async,
        }

    def test_update(self):
        resp = self.client.put(
            self.detail_url, {"foo": "bar"}, content_type="application/json"
        )
        assert resp.status_code == 200
        assert resp.data == {
            "method": "PUT",
            "data": {"foo": "bar"},
            "async": self.use_async,
        }

    def test_partial_update(self):
        resp = self.client.patch(
            self.detail_url, {"foo": "bar"}, content_type="application/json"
        )
        assert resp.status_code == 200
        assert resp.data == {
            "method": "PATCH",
            "data": {"foo": "bar"},
            "async": self.use_async,
        }

    def test_destroy(self):
        resp = self.client.delete(self.detail_url)
        assert resp.status_code == 200
        assert resp.data == {"method": "DELETE", "async": self.use_async}


class TestSyncRouterIntegrationTests(_RouterIntegrationTests):
    use_async = False
    __test__ = True


class AsyncRouterIntegrationTests(_RouterIntegrationTests):
    use_async = True
    __test__ = True
