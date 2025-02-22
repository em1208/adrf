import inspect
from collections.abc import Mapping

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ForeignKey
from django.db.models import Model


# NOTE This function was taken from the python library and modified
# to allow an exclusion list and avoid recursion errors.
def getmembers(object, predicate, exclude_names=[]):
    results = []
    processed = set()
    names = [x for x in dir(object) if x not in exclude_names]
    if inspect.isclass(object):
        mro = inspect.getmro(object)
        # add any DynamicClassAttributes to the list of names if object is a class;
        # this may result in duplicate entries if, for example, a virtual
        # attribute with the same name as a DynamicClassAttribute exists
        try:
            for base in object.__bases__:
                for k, v in base.__dict__.items():
                    if isinstance(v, inspect.types.DynamicClassAttribute) and k not in exclude_names:
                        names.append(k)
        except AttributeError:
            pass
    else:
        mro = ()
    for key in names:
        # First try to get the value via getattr.  Some descriptors don't
        # like calling their __get__ (see bug #1785), so fall back to
        # looking in the __dict__.
        try:
            value = getattr(object, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                # could be a (currently) missing slot member, or a buggy
                # __dir__; discard and move on
                continue
        if not predicate or predicate(value):
            results.append((key, value))
        processed.add(key)
    results.sort(key=lambda pair: pair[0])
    return results


class async_attrgetter:
    """
    Return a callable object that fetches the given attribute(s) from its operand asynchronously.
    After f = async_attrgetter('name'), the call await f(r) returns r.name.
    After g = async_attrgetter('name', 'date'), the call await g(r) returns (r.name, r.date).
    After h = async_attrgetter('name.first', 'name.last'), the call await h(r) returns
    (r.name.first, r.name.last).
    """

    __slots__ = ("_attrs", "_call")

    def __init__(self, attr, *attrs):
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError("attribute name must be a string")
            self._attrs = (attr,)
            names = attr.split(".")

            async def func(obj):
                for name in names:
                    # Проверяем, является ли текущий атрибут внешним ключом
                    if (
                        isinstance(obj, Model)
                        and name in [f.name for f in obj.__class__._meta.fields]
                        and isinstance(obj.__class__._meta.get_field(name), ForeignKey)
                    ):
                        # Если это внешний ключ, выполняем асинхронный запрос
                        obj = await obj.__class__.objects.select_related(name).aget(pk=obj.pk)
                    obj = getattr(obj, name)
                return obj

            self._call = func
        else:
            self._attrs = (attr,) + attrs
            getters = tuple(map(async_attrgetter, self._attrs))

            async def func(obj):
                return tuple(await getter(obj) for getter in getters)

            self._call = func

    async def __call__(self, obj):
        return await self._call(obj)

    def __repr__(self):
        return "%s.%s(%s)" % (self.__class__.__module__, self.__class__.__qualname__, ", ".join(map(repr, self._attrs)))

    def __reduce__(self):
        return self.__class__, self._attrs


async def aget_attribute(instance, attrs):
    """
    Similar to Python's built in `getattr(instance, attr)`,
    but takes a list of nested attributes, instead of a single attribute.

    Also accepts either attribute lookup on objects or dictionary lookups.
    This version is asynchronous and supports Django ORM's async methods.
    """
    for attr in attrs:
        try:
            if isinstance(instance, Mapping):
                instance = instance[attr]
            else:
                # Проверяем, является ли instance моделью Django
                if isinstance(instance, Model):
                    # Получаем поле модели
                    field = instance.__class__._meta.get_field(attr)
                    # Если это внешний ключ, выполняем асинхронный запрос
                    if isinstance(field, ForeignKey):
                        instance = await instance.__class__.objects.select_related(attr).aget(pk=instance.pk)
                # Получаем атрибут
                instance = getattr(instance, attr)
        except ObjectDoesNotExist:
            return None
        except (AttributeError, KeyError):
            # Если атрибут не найден, возвращаем None
            return None

        # Если атрибут является callable-объектом, вызываем его
        if callable(instance):
            try:
                if is_async_callable(instance):
                    instance = await instance()
                else:
                    instance = instance()
            except (AttributeError, KeyError) as exc:
                # Если вызов callable вызвал исключение, поднимаем ValueError
                raise ValueError(f'Exception raised in callable attribute "{attr}"; original exception was: {exc}')

    return instance


def is_async_callable(obj):
    """
    Проверяет, является ли объект асинхронно вызываемым.
    Использует модуль inspect для более надёжной проверки.
    """
    if not callable(obj):
        return False
    # Проверяем, является ли объект асинхронной функцией или методом
    if inspect.iscoroutinefunction(obj):
        return True
    # Проверяем, является ли объект асинхронным callable объектом (например, объект с методом __call__)
    if inspect.isawaitable(obj) and hasattr(obj, "__call__"):
        return True
    return False
