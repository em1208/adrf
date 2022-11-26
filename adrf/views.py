from asgiref.sync import sync_to_async

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView as DRFAPIView


class APIView(DRFAPIView):
    def sync_dispatch(self, request, *args, **kwargs):
        """
        `.sync_dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    async def async_dispatch(self, request, *args, **kwargs):
        """
        `.async_dispatch()` is pretty much the same as Django's regular dispatch,
        except for awaiting the handler function and with extra hooks for startup,
        finalize, and exception handling.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)
        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            await sync_to_async(self.initial)(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            response = await handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response

    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch checks if the view is async or not and uses the respective
        async or sync dispatch method.
        """
        if getattr(self, 'view_is_async', False):
            return self.async_dispatch(request, *args, **kwargs)
        else:
            return self.sync_dispatch(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        """
        Handler method for HTTP 'OPTIONS' request.
        """
        def func():
            if self.metadata_class is None:
                return self.http_method_not_allowed(request, *args, **kwargs)
            data = self.metadata_class().determine_metadata(request, self)
            return Response(data, status=status.HTTP_200_OK)

        if getattr(self, 'view_is_async', False):
            async def handler():
                return await sync_to_async(func)()
        else:
            def handler():
                return func()
        return handler()
