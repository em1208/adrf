# Async Django REST framework

**Async support for Django REST framework**

# Requirements

* Python 3.8+
* Django 4.1

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

# Example

# Async Views

When using Django 4.1 and above, this package allows you to work with async class and function based views.

For class based views, all handler methods must be async, otherwise Django will raise an exception. For function based views, the function itself must be async.

For example:

    from adrf.views import APIView

    class AsyncView(APIView):
        async def get(self, request):
            return Response({"message": "This is an async class based view."})

    from adrf.decorators import api_view

    @api_view(['GET'])
    async def async_view(request):
        return Response({"message": "This is an async function based view."})
