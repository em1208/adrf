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

class AsyncThrottle(BaseThrottle):
    async def allow_request(self, request, view) -> bool:
        if random.random() < 0.7:
            return False

        return True

    async def wait(self):
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
from . import serializers
from adrf.views import APIView

class AsyncView(APIView):
    async def get(self, request):
        data = {
            "username": "test",
            "password": "test",
            "age": 10,
        }
        serializer = serializers.AsyncSerializer(data=data)
        serializer.is_valid()
        return await serializer.adata
```
