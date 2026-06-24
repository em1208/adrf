from rest_framework import serializers as drf_serializers

try:
    from inspect import iscoroutinefunction
except ImportError:
    from asyncio import iscoroutinefunction


class SerializerMethodField(drf_serializers.SerializerMethodField):
    async def ato_representation(self, attribute):
        method = getattr(self.parent, self.method_name)
        return await method(attribute)


class AsyncFieldMixin:
    async def ato_representation(self, value):
        if iscoroutinefunction(value):
            value = await value
        return super().to_representation(value)


class BigIntegerField(AsyncFieldMixin, drf_serializers.BigIntegerField):
    pass


class IntegerField(AsyncFieldMixin, drf_serializers.IntegerField):
    pass


class BooleanField(AsyncFieldMixin, drf_serializers.BooleanField):
    pass


class CharField(AsyncFieldMixin, drf_serializers.CharField):
    pass


class ChoiceField(AsyncFieldMixin, drf_serializers.ChoiceField):
    pass


class DateField(AsyncFieldMixin, drf_serializers.DateField):
    pass


class DateTimeField(AsyncFieldMixin, drf_serializers.DateTimeField):
    pass


class DecimalField(AsyncFieldMixin, drf_serializers.DecimalField):
    pass


class DictField(AsyncFieldMixin, drf_serializers.DictField):
    pass


class DurationField(AsyncFieldMixin, drf_serializers.DurationField):
    pass


class EmailField(AsyncFieldMixin, drf_serializers.EmailField):
    pass


class Field(AsyncFieldMixin, drf_serializers.Field):
    pass


class FileField(AsyncFieldMixin, drf_serializers.FileField):
    pass


class FilePathField(AsyncFieldMixin, drf_serializers.FilePathField):
    pass


class FloatField(AsyncFieldMixin, drf_serializers.FloatField):
    pass


class HiddenField(AsyncFieldMixin, drf_serializers.HiddenField):
    pass


class HStoreField(AsyncFieldMixin, drf_serializers.HStoreField):
    pass


class IPAddressField(AsyncFieldMixin, drf_serializers.IPAddressField):
    pass


class ImageField(AsyncFieldMixin, drf_serializers.ImageField):
    pass


class JSONField(AsyncFieldMixin, drf_serializers.JSONField):
    pass


class ListField(AsyncFieldMixin, drf_serializers.ListField):
    pass


class ModelField(AsyncFieldMixin, drf_serializers.ModelField):
    pass


class MultipleChoiceField(AsyncFieldMixin, drf_serializers.MultipleChoiceField):
    pass


class ReadOnlyField(AsyncFieldMixin, drf_serializers.ReadOnlyField):
    pass


class RegexField(AsyncFieldMixin, drf_serializers.RegexField):
    pass


class SlugField(AsyncFieldMixin, drf_serializers.SlugField):
    pass


class TimeField(AsyncFieldMixin, drf_serializers.TimeField):
    pass


class URLField(AsyncFieldMixin, drf_serializers.URLField):
    pass


class UUIDField(AsyncFieldMixin, drf_serializers.UUIDField):
    pass
