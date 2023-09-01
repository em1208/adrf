from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from adrf.viewsets import ViewSet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.test import APIRequestFactory
from tests.test_views import JSON_ERROR, sanitise_json_error

factory = APIRequestFactory()


class BasicViewSet(ViewSet):
    def list(self, request):
        return Response({'method': 'GET'})

    def create(self, request, *args, **kwargs):
        return Response({'method': 'POST', 'data': request.data})


class AsyncViewSet(ViewSet):
    async def list(self, request):
        return Response({'method': 'GET'})

    async def create(self, request, *args, **kwargs):
        return Response({'method': 'POST', 'data': request.data})


class ViewSetIntegrationTests(TestCase):
    def setUp(self):
        self.list = BasicViewSet.as_view({"get": "list"})
        self.create = BasicViewSet.as_view({"post": "create"})

    def test_get_succeeds(self):
        request = factory.get('/')
        response = self.list(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'method': 'GET'}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user('user', 'user@example.com', 'password')
        request = factory.get('/')
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = self.list(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'method': 'GET'}

    def test_post_succeeds(self):
        request = factory.post('/', {'test': 'foo'})
        response = self.create(request)
        expected = {
            'method': 'POST',
            'data': {'test': ['foo']}
        }
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options('/')
        response = self.list(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post('/', 'f00bar', content_type='application/json')
        response = self.create(request)
        expected = {
            'detail': JSON_ERROR
        }
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected


class AsyncViewSetIntegrationTests(TestCase):
    def setUp(self):
        self.list = AsyncViewSet.as_view({"get": "list"})
        self.create = AsyncViewSet.as_view({"post": "create"})

    def test_get_succeeds(self):
        request = factory.get('/')
        response = async_to_sync(self.list)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'method': 'GET'}

    def test_logged_in_get_succeeds(self):
        user = User.objects.create_user('user', 'user@example.com', 'password')
        request = factory.get('/')
        # del is used to force the ORM to query the user object again
        del user.is_active
        request.user = user
        response = async_to_sync(self.list)(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'method': 'GET'}

    def test_post_succeeds(self):
        request = factory.post('/', {'test': 'foo'})
        response = async_to_sync(self.create)(request)
        expected = {
            'method': 'POST',
            'data': {'test': ['foo']}
        }
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_options_succeeds(self):
        request = factory.options('/')
        response = async_to_sync(self.list)(request)
        assert response.status_code == status.HTTP_200_OK

    def test_400_parse_error(self):
        request = factory.post('/', 'f00bar', content_type='application/json')
        response = async_to_sync(self.create)(request)
        expected = {
            'detail': JSON_ERROR
        }
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert sanitise_json_error(response.data) == expected


class MisconfiguredViewSetIntegrationTests(TestCase):
    def test_as_view_raises_misconfigured_exception(self):
        class MisconfiguredViewSet(AsyncViewSet):
            def destroy(self, request):
                return Response({'method': 'DELETE'})

        with self.assertRaises(ImproperlyConfigured):
            MisconfiguredViewSet.as_view({"get": "list", "delete": "destroy"})

    def test_as_view_does_not_raise_if_non_action_handler_is_sync(self):
        class SafeSerializer(BaseSerializer):
            ...

        class SafeViewSet(AsyncViewSet):
            serializer_class = SafeSerializer

            def my_func(self):
                pass

        try:
            SafeViewSet.as_view({'delete': 'destroy'})
        except ImproperlyConfigured as exc:
            self.fail('ImproperlyConfigured unexpectedly raised', exc)
