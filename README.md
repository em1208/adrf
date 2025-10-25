# Async Django REST framework

**Async support for Django REST framework**

# Requirements

* Python 3.8+
* Django 4.1+

We **highly recommend** and only officially support the latest patch release of
each Python and Django series.

# Installation

Install using `pip`...

    pip install adrf

Add `'adrf'` to your `INSTALLED_APPS` setting.
```python
INSTALLED_APPS = [
    ...
    'adrf',
]
```

# Examples

# Async Views

When using Django 4.1 and above, this package allows you to work with async class and function based views.

For class based views, all handler methods must be async, otherwise Django will raise an exception. For function based views, the function itself must be async.

For example:

```python
from adrf.views import APIView

class AsyncAuthentication(BaseAuthentication):
    async def authenticate(self, request) -> tuple[User, None]:
        return user, None

class AsyncPermission:
    async def has_permission(self, request, view) -> bool:
        if random.random() < 0.7:
            return False

        return True

    async def has_object_permission(self, request, view, obj):
        if obj.user == request.user or request.user.is_superuser:
            return True

        return False

class AsyncThrottle(BaseThrottle):
    async def allow_request(self, request, view) -> bool:
        if random.random() < 0.7:
            return False

        return True

    def wait(self):
        return 3

class AsyncView(APIView):
    authentication_classes = [AsyncAuthentication]
    permission_classes = [AsyncPermission]
    throttle_classes = [AsyncThrottle]

    async def get(self, request):
        return Response({"message": "This is an async class based view."})

from adrf.decorators import api_view

@api_view(['GET'])
async def async_view(request):
    return Response({"message": "This is an async function based view."})
```
# Async ViewSets

For viewsets, all handler methods must be async too.

views.py
```python
from django.contrib.auth import get_user_model
from rest_framework.response import Response

from adrf.viewsets import ViewSet


User = get_user_model()


class AsyncViewSet(ViewSet):

    async def list(self, request):
        return Response(
            {"message": "This is the async `list` method of the viewset."}
        )

    async def retrieve(self, request, pk):
        user = await User.objects.filter(pk=pk).afirst()
        return Response({"user_pk": user and user.pk})

```

urls.py
```python
from django.urls import path, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r"async_viewset", views.AsyncViewSet, basename="async")

urlpatterns = [
    path("", include(router.urls)),
]

```

## ModelViewSet Routing

The `ModelViewSet` implementation included with adrf provides asynchronous CRUD actions (e.g., `aretrieve`, `acreate`, `aupdate`, and `alist`). However, these actions are not invoked by default when using the router implementation in `rest_framework`. To have these async methods mapped by default, use adrf's router instead:

```python
from django.urls import path, include
from adrf import routers    # import the adrf router instead

from . import views

router = routers.DefaultRouter()
router.register(r"async_viewset", views.AsyncModelViewSet, basename="async")

urlpatterns = [
    path("", include(router.urls)),
]

```

# Async Serializers

serializers.py

```python
from adrf.serializers import Serializer
from rest_framework import serializers

class AsyncSerializer(Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    age = serializers.IntegerField()
```

views.py

```python
from .serializers import AsyncSerializer
from adrf.views import APIView

class AsyncView(APIView):
    async def get(self, request):
        data = {
            "username": "test",
            "password": "test",
            "age": 10,
        }
        serializer = AsyncSerializer(data=data)
        serializer.is_valid()
        return await serializer.adata
```

# Async Generics

models.py

```python
from django.db import models

class Order(models.Model):
    name = models.TextField()
```

serializers.py

```python
from adrf.serializers import ModelSerializer
from .models import Order

class OrderSerializer(ModelSerializer):
    class Meta:
        model = Order
        fields = ('name', )
```

views.py

```python
from adrf.generics import ListCreateAPIView
from .models import Order
from .serializers import OrderSerializer

class ListCreateOrderView(ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
```
