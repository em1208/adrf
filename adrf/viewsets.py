import asyncio
from functools import update_wrapper

from adrf.views import APIView
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import classonlymethod
from django.utils.functional import classproperty
from rest_framework.viewsets import ViewSetMixin as DRFViewSetMixin


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
            raise TypeError("The `actions` argument must be provided when "
                            "calling `.as_view()` on a ViewSet. For example "
                            "`.as_view({'get': 'list'})`")

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        # name and suffix are mutually exclusive
        if 'name' in initkwargs and 'suffix' in initkwargs:
            raise TypeError(
                "%s() received both `name` and `suffix`, which are "
                "mutually exclusive arguments." % (cls.__name__))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)

            if 'get' in actions and 'head' not in actions:
                actions['head'] = actions['get']

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

            if 'get' in actions and 'head' not in actions:
                actions['head'] = actions['get']

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

    @classproperty
    def view_is_async(cls):
        """
        Checks whether viewset methods are coroutines.
        """
        result = [
            asyncio.iscoroutinefunction(function)
            for name, function in cls.__dict__.items()
            if callable(function) and not name.startswith("__")
        ]
        is_async = any(result)
        if is_async and not all(result):
            raise ImproperlyConfigured(
                f"{cls.__qualname__} action handlers must either be all sync "
                "or all async."
            )
        return is_async
