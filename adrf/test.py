from django.conf import settings
from django.test.client import AsyncClient as DjangoAsyncClient
from django.test.client import AsyncClientHandler
from django.test.client import AsyncRequestFactory as DjangoAsyncRequestFactory
from django.utils.encoding import force_bytes
from django.utils.http import urlencode
from rest_framework.settings import api_settings
from rest_framework.test import force_authenticate


class AsyncForceAuthClientHandler(AsyncClientHandler):
    """
    A patched version of ClientHandler that can enforce authentication
    on the outgoing requests.
    """

    def __init__(self, *args, **kwargs):
        self._force_user = None
        self._force_token = None
        super().__init__(*args, **kwargs)

    def get_response(self, request):
        # This is the simplest place we can hook into to patch the
        # request object.
        force_authenticate(request, self._force_user, self._force_token)
        return super().get_response(request)


class AsyncAPIRequestFactory(DjangoAsyncRequestFactory):
    renderer_classes_list = api_settings.TEST_REQUEST_RENDERER_CLASSES
    default_format = api_settings.TEST_REQUEST_DEFAULT_FORMAT

    def __init__(self, enforce_csrf_checks=False, **defaults):
        self.enforce_csrf_checks = enforce_csrf_checks
        self.renderer_classes = {}
        for cls in self.renderer_classes_list:
            self.renderer_classes[cls.format] = cls
        super().__init__(**defaults)

    def _encode_data(self, data, format=None, content_type=None):
        """
        Encode the data returning a two tuple of (bytes, content_type)
        """

        if data is None:
            return ("", content_type)

        assert (
            format is None or content_type is None
        ), "You may not set both `format` and `content_type`."

        if content_type:
            # Content type specified explicitly, treat data as a raw bytestring
            ret = force_bytes(data, settings.DEFAULT_CHARSET)

        else:
            format = format or self.default_format

            assert format in self.renderer_classes, (
                "Invalid format '{}'. Available formats are {}. "
                "Set TEST_REQUEST_RENDERER_CLASSES to enable "
                "extra request formats.".format(
                    format,
                    ", ".join(["'" + fmt + "'" for fmt in self.renderer_classes]),
                )
            )

            # Use format and render the data into a bytestring
            renderer = self.renderer_classes[format]()
            ret = renderer.render(data)

            # Determine the content-type header from the renderer
            content_type = renderer.media_type
            if renderer.charset:
                content_type = "{}; charset={}".format(content_type, renderer.charset)

            # Coerce text to bytes if required.
            if isinstance(ret, str):
                ret = ret.encode(renderer.charset)

        return ret, content_type

    def get(self, path, data=None, **extra):
        r = {
            "QUERY_STRING": urlencode(data or {}, doseq=True),
        }
        if not data and "?" in path:
            # Fix to support old behavior where you have the arguments in the
            # url. See #1461.
            query_string = force_bytes(path.split("?")[1])
            query_string = query_string.decode("iso-8859-1")
            r["QUERY_STRING"] = query_string
        r.update(extra)
        return self.generic("GET", path, **r)

    def post(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic("POST", path, data, content_type, **extra)

    def put(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic("PUT", path, data, content_type, **extra)

    def patch(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic("PATCH", path, data, content_type, **extra)

    def delete(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic("DELETE", path, data, content_type, **extra)

    def options(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic("OPTIONS", path, data, content_type, **extra)

    def generic(
        self,
        method,
        path,
        data="",
        content_type="application/octet-stream",
        secure=False,
        **extra,
    ):
        # Include the CONTENT_TYPE, regardless of whether or not data is empty.
        if content_type is not None:
            extra["CONTENT_TYPE"] = str(content_type)

        return super().generic(method, path, data, content_type, secure, **extra)

    def request(self, **kwargs):
        request = super().request(**kwargs)
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks
        return request


class AsyncAPIClient(DjangoAsyncClient, AsyncAPIRequestFactory):
    """
    An async version of APIClient that creates ASGIRequests and calls through an
    async request path.

    Does not currently support "follow" on its methods.
    """

    def __init__(self, enforce_csrf_checks=False, **defaults):
        super().__init__(**defaults)
        self.handler = AsyncForceAuthClientHandler(enforce_csrf_checks)
        self._credentials = {}

    def credentials(self, **kwargs):
        """
        Sets headers that will be used on every outgoing request.
        """
        self._credentials = kwargs

    def force_authenticate(self, user=None, token=None):
        """
        Forcibly authenticates outgoing requests with the given
        user and/or token.
        """
        self.handler._force_user = user
        self.handler._force_token = token
        if user is None and token is None:
            self.logout()  # Also clear any possible session info if required

    async def request(self, **kwargs):
        # Ensure that any credentials set get added to every request.
        kwargs.update(self._credentials)
        return await super().request(**kwargs)

    def get(self, path, data=None, **extra):
        response = super().get(path, data=data, **extra)
        return response

    def post(self, path, data=None, format=None, content_type=None, **extra):
        response = super().post(
            path, data=data, format=format, content_type=content_type, **extra
        )
        return response

    def put(self, path, data=None, format=None, content_type=None, **extra):
        response = super().put(
            path, data=data, format=format, content_type=content_type, **extra
        )
        return response

    def patch(self, path, data=None, format=None, content_type=None, **extra):
        response = super().patch(
            path, data=data, format=format, content_type=content_type, **extra
        )
        return response

    def delete(self, path, data=None, format=None, content_type=None, **extra):
        response = super().delete(
            path, data=data, format=format, content_type=content_type, **extra
        )
        return response

    def options(self, path, data=None, format=None, content_type=None, **extra):
        response = super().options(
            path, data=data, format=format, content_type=content_type, **extra
        )
        return response

    def logout(self):
        self._credentials = {}

        # Also clear any `force_authenticate`
        self.handler._force_user = None
        self.handler._force_token = None

        if self.session:
            super().logout()
