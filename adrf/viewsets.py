import asyncio
from functools import update_wrapper

from asgiref.sync import async_to_sync, sync_to_async
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.decorators import classonlymethod
from django.utils.functional import classproperty

from adrf.views import APIView
from adrf.shortcuts import aget_object_or_404
from rest_framework.viewsets import ViewSetMixin as DRFViewSetMixin
from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework import status


class ViewSetMixin(DRFViewSetMixin):
    """
    This is the magic.

    Overrides `.as_view()` so that it takes an `actions` keyword that performs
    the binding of HTTP methods to actions on the Resource.

    For example, to create a concrete view binding the 'GET' and 'POST' methods
    to the 'list' and 'create' actions...

    view = MyViewSet.as_view({'get': 'list', 'post': 'create'})
    """

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        """
        Because of the way class based views create a closure around the
        instantiated view, we need to totally reimplement `.as_view`,
        and slightly modify the view function that is created and returned.
        """
        # The name and description initkwargs may be explicitly overridden for
        # certain route configurations. eg, names of extra actions.
        cls.name = None
        cls.description = None
        # The suffix initkwarg is reserved for displaying the viewset type.
        # This initkwarg should have no effect if the name is provided.
        # eg. 'List' or 'Instance'.
        cls.suffix = None

        # The detail initkwarg is reserved for introspecting the viewset type.
        cls.detail = None

        # Setting a basename allows a view to reverse its action urls. This
        # value is provided by the router through the initkwargs.
        cls.basename = None

        # actions must not be empty
        if not actions:
            raise TypeError(
                "The `actions` argument must be provided when "
                "calling `.as_view()` on a ViewSet. For example "
                "`.as_view({'get': 'list'})`"
            )

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(
                    "You tried to pass in the %s method name as a "
                    "keyword argument to %s(). Don't do that." % (key, cls.__name__)
                )
            if not hasattr(cls, key):
                raise TypeError(
                    "%s() received an invalid keyword %r" % (cls.__name__, key)
                )

        # name and suffix are mutually exclusive
        if "name" in initkwargs and "suffix" in initkwargs:
            raise TypeError(
                "%s() received both `name` and `suffix`, which are "
                "mutually exclusive arguments." % (cls.__name__)
            )

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)

            if "get" in actions and "head" not in actions:
                actions["head"] = actions["get"]

            # We also store the mapping of request methods to actions,
            # so that we can later set the action attribute.
            # eg. `self.action = 'list'` on an incoming GET request.
            self.action_map = actions

            # Bind methods to actions
            # This is the bit that's different to a standard view
            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            self.request = request
            self.args = args
            self.kwargs = kwargs

            # or continue as usual
            return self.dispatch(request, *args, **kwargs)

        async def async_view(request, *args, **kwargs):
            self = cls(**initkwargs)

            if "get" in actions and "head" not in actions:
                actions["head"] = actions["get"]

            # We also store the mapping of request methods to actions,
            # so that we can later set the action attribute.
            # eg. `self.action = 'list'` on an incoming GET request.
            self.action_map = actions

            # Bind methods to actions
            # This is the bit that's different to a standard view
            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            self.request = request
            self.args = args
            self.kwargs = kwargs

            # or continue as usual
            return await self.dispatch(request, *args, **kwargs)

        view = async_view if cls.view_is_async else view

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())

        # We need to set these on the view function, so that breadcrumb
        # generation can pick out these bits of information from a
        # resolved URL.
        view.cls = cls
        view.initkwargs = initkwargs
        view.actions = actions
        view.csrf_exempt = True
        return view


class ViewSet(ViewSetMixin, APIView):
    _ASYNC_NON_DISPATCH_METHODS = []
    
    @classproperty
    def view_is_async(cls):
        """
        Checks whether any viewset methods are coroutines.
        """
        result = [
            asyncio.iscoroutinefunction(function)
            for name, function in cls.__dict__.items()
            if callable(function) and not name.startswith("__") 
                and not name in cls._ASYNC_NON_DISPATCH_METHODS
        ]
        return any(result)

class GenericViewSet(ViewSet):
    """
    Base class for all other generic views.
    """
    _ASYNC_NON_DISPATCH_METHODS = ViewSet._ASYNC_NON_DISPATCH_METHODS \
                                + ['aget_object', 'perform_create', 'apaginate_queryset']
    
    queryset = None
    serializer_class = None

    # If you want to use object lookups other than pk, set 'lookup_field'.
    # For more complex lookup requirements override `get_object()`.
    lookup_field = 'pk'
    lookup_url_kwarg = None

    # The filter backend classes to use for queryset filtering
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS

    # The style to use for queryset pagination.
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    # Allow generic typing checking for generic views.
    def __class_getitem__(cls, *args, **kwargs):
        return cls

    def get_queryset(self):
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.

        This method should always be used rather than accessing `self.queryset`
        directly, as `self.queryset` gets evaluated only once, and those results
        are cached for all subsequent requests.

        You may want to override this if you need to provide different
        querysets depending on the incoming request.

        (Eg. return a list of items that is specific to the user)
        """
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
        return queryset
    
    async def aget_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = await aget_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )

        return self.serializer_class

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        if asyncio.iscoroutinefunction(self.paginator.paginate_queryset):
            return async_to_sync(self.paginator.paginate_queryset(queryset, self.request, view=self))
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    async def apaginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        if asyncio.iscoroutinefunction(self.paginator.paginate_queryset):
            return await self.paginator.paginate_queryset(queryset, self.request, view=self)
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        if asyncio.iscoroutinefunction(self.paginator.get_paginated_response):
            return async_to_sync(self.paginator.get_paginated_response(data))
        return self.paginator.get_paginated_response(data)

class CreateModelMixin:
    """
    Create a model instance.
    """
    async def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        await self.perform_create(serializer)
        data = await serializer.adata
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    async def perform_create(self, serializer):
        await serializer.asave()

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}

class RetrieveModelMixin:
    """
    Retrieve a model instance.
    """
    async def retrieve(self, request, *args, **kwargs):
        instance = await self.aget_object()
        serializer = self.get_serializer(instance, many=False)
        #try to serialize async is the serializer supports it. Sync otherwise
        data = await serializer.adata if hasattr(serializer, 'adata') else serializer.data
        return Response(data, status=status.HTTP_200_OK)
        
class ListModelMixin:
    """
    List a queryset.
    """
    async def list(self, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = await self.apaginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = await serializer.adata if hasattr(serializer, 'adata') else serializer.data
            return await self.aget_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        data = await serializer.adata if hasattr(serializer, 'adata') else serializer.data
        return Response(data, status=status.HTTP_200_OK)
