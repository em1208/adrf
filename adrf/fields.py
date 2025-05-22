import inspect
from typing import Mapping
from typing import Union

from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.fields import _UnvalidatedField
from rest_framework.fields import BooleanField as DRFBooleanField
from rest_framework.fields import BuiltinSignatureError
from rest_framework.fields import CharField as DRFCharField
from rest_framework.fields import ChoiceField as DRFChoiceField
from rest_framework.fields import DateField as DRFDateField
from rest_framework.fields import DateTimeField as DRFDateTimeField
from rest_framework.fields import DecimalField as DRFDecimalField
from rest_framework.fields import DictField as DRFDictField
from rest_framework.fields import DurationField as DRFDurationField
from rest_framework.fields import EmailField as DRFEmailField
from rest_framework.fields import empty
from rest_framework.fields import Field
from rest_framework.fields import FileField as DRFFileField
from rest_framework.fields import FilePathField as DRFFilePathField
from rest_framework.fields import FloatField as DRFFloatField
from rest_framework.fields import get_error_detail
from rest_framework.fields import HiddenField as DRFHiddenField
from rest_framework.fields import HStoreField as DRFHStoreField
from rest_framework.fields import ImageField as DRFImageField
from rest_framework.fields import IntegerField as DRFIntegerField
from rest_framework.fields import IPAddressField as DRFIPAddressForeign
from rest_framework.fields import JSONField as DRFJSONField
from rest_framework.fields import ListField as DRFListField
from rest_framework.fields import ModelField as DRFModelField
from rest_framework.fields import MultipleChoiceField as DRFMultipleChoiceField
from rest_framework.fields import ReadOnlyField as DRFReadOnlyField
from rest_framework.fields import RegexField as DRFRegexField
from rest_framework.fields import SerializerMethodField as DRFSerializerMethodField
from rest_framework.fields import SkipField
from rest_framework.fields import SlugField as DRFSlugField
from rest_framework.fields import TimeField as DRFTimeField
from rest_framework.fields import URLField as DRFURLField
from rest_framework.fields import UUIDField as DRFUUIDField
from rest_framework.utils import html

from adrf.utils import aget_attribute


class AsyncFieldMixin:
    async def avalidate_empty_values(self, data):
        """
        Асинхронная версия validate_empty_values.
        """
        if self.read_only:
            return (True, await self.aget_default())

        if data is empty:
            if getattr(self.root, "partial", False):
                raise SkipField()
            if self.required:
                self.fail("required")
            return (True, await self.aget_default())

        if data is None:
            if not self.allow_null:
                self.fail("null")
            elif self.source == "*":
                return (False, None)
            return (True, None)

        return (False, data)

    async def arun_validation(self, data=empty):
        """
        Асинхронная версия run_validation.
        """
        is_empty_value, data = await self.avalidate_empty_values(data)
        if is_empty_value:
            return data
        value = await self.ato_internal_value(data)
        await self.arun_validators(value)
        return value

    async def arun_validators(self, value):
        """
        Асинхронная версия run_validators.
        """
        errors = []
        for validator in self.validators:
            try:
                if getattr(validator, "requires_context", False):
                    if inspect.iscoroutinefunction(validator):
                        await validator(value, self)
                    else:
                        await sync_to_async(validator)(value, self)
                else:
                    if inspect.iscoroutinefunction(validator):
                        await validator(value)
                    else:
                        await sync_to_async(validator)(value)
            except ValidationError as exc:
                if isinstance(exc.detail, dict):
                    raise
                errors.extend(exc.detail)
            except DjangoValidationError as exc:
                errors.extend(get_error_detail(exc))
        if errors:
            raise ValidationError(errors)

    async def ato_internal_value(self, data):
        """
        Асинхронная версия to_internal_value.
        Должна быть переопределена в дочерних классах.
        """
        raise NotImplementedError(
            "{cls}.ato_internal_value() must be implemented for field "
            "{field_name}.".format(
                cls=self.__class__.__name__,
                field_name=self.field_name,
            )
        )

    async def ato_representation(self, value):
        """
        Асинхронная версия to_representation.
        Должна быть переопределена в дочерних классах.
        """
        raise NotImplementedError(
            "{cls}.ato_representation() must be implemented for field {field_name}.".format(
                cls=self.__class__.__name__,
                field_name=self.field_name,
            )
        )

    async def aget_default(self):
        """
        Асинхронная версия get_default.
        """
        if self.default is empty or getattr(self.root, "partial", False):
            raise SkipField()
        if callable(self.default):
            if getattr(self.default, "requires_context", False):
                if inspect.iscoroutinefunction(self.default):
                    return await self.default(self)
                return self.default(self)
            else:
                if inspect.isfunction(self.default):
                    return await self.default(self)
                return self.default()
        return self.default


class AsyncField(Field, AsyncFieldMixin):
    """
    Базовый класс для всех асинхронных полей.
    Наследует синхронные методы из Field и асинхронные из AsyncFieldMixin.
    """

    async def aget_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        try:
            return await aget_attribute(instance, self.source_attrs)
        except BuiltinSignatureError as exc:
            msg = (
                "Field source for `{serializer}.{field}` maps to a built-in "
                "function type and is invalid. Define a property or method on "
                "the `{instance}` instance that wraps the call to the built-in "
                "function.".format(
                    serializer=self.parent.__class__.__name__,
                    field=self.field_name,
                    instance=instance.__class__.__name__,
                )
            )
            raise type(exc)(msg)
        except (KeyError, AttributeError) as exc:
            if self.default is not empty:
                return self.get_default()
            if self.allow_null:
                return None
            if not self.required:
                raise SkipField()
            msg = (
                "Got {exc_type} when attempting to get a value for field "
                "`{field}` on serializer `{serializer}`.\nThe serializer "
                "field might be named incorrectly and not match "
                "any attribute or key on the `{instance}` instance.\n"
                "Original exception text was: {exc}.".format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc,
                )
            )
            raise type(exc)(msg)


class BooleanField(DRFBooleanField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class CharField(DRFCharField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class EmailField(DRFEmailField, CharField):
    pass


class RegexField(DRFRegexField, CharField):
    pass


class SlugField(DRFSlugField, CharField):
    pass


class URLField(DRFURLField, CharField):
    pass


class UUIDField(DRFUUIDField, AsyncField):
    pass


class IPAddressField(DRFIPAddressForeign, AsyncField):
    pass


class IntegerField(DRFIntegerField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class FloatField(DRFFloatField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class DecimalField(DRFDecimalField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class DateTimeField(DRFDateTimeField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class DateField(DRFDateField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class TimeField(DRFTimeField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class DurationField(DRFDurationField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class ChoiceField(DRFChoiceField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class MultipleChoiceField(DRFMultipleChoiceField, ChoiceField):
    pass


class FilePathField(DRFFilePathField, ChoiceField):
    pass


class FileField(DRFFileField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class ImageField(DRFImageField, FileField):
    pass


class ListField(DRFListField, AsyncField):
    child: Union[Field, AsyncField] = _UnvalidatedField()

    async def arun_validation(self, data=empty):
        if html.is_html_input(data):
            data = html.parse_html_list(data, default=[])
        if isinstance(data, (str, Mapping)) or not hasattr(data, "__iter__"):
            self.fail("not_a_list", input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")
        return await self.arun_child_validation(data)

    async def arun_child_validation(self, data):
        result = []
        errors = {}

        for idx, item in enumerate(data):
            try:
                if hasattr(self.child, "arun_validation"):
                    validated_item = await self.child.arun_validation(item)
                else:
                    validated_item = self.child.run_validation(item)
                result.append(validated_item)
            except ValidationError as e:
                errors[idx] = e.detail
            except DjangoValidationError as e:
                errors[idx] = get_error_detail(e)

        if not errors:
            return result
        raise ValidationError(errors)

    async def ato_representation(self, value):
        result = []
        if hasattr(value, "__aiter__"):
            async for item in value:
                if item is not None:
                    if hasattr(self.child, "ato_representation"):
                        result.append(await self.child.ato_representation(item))
                    else:
                        result.append(self.child.to_representation(item))
                else:
                    result.append(None)
        else:
            for item in value:
                if item is not None:
                    if hasattr(self.child, "ato_representation"):
                        result.append(await self.child.ato_representation(item))
                    else:
                        result.append(self.child.to_representation(item))
                else:
                    result.append(None)
        return result


class DictField(DRFDictField, AsyncField):
    child: Union[Field, AsyncField] = _UnvalidatedField()

    async def ato_internal_value(self, data):
        """
        Dicts of native values <- Dicts of primitive datatypes.
        """
        if html.is_html_input(data):
            data = html.parse_html_dict(data)
        if not isinstance(data, dict):
            self.fail("not_a_dict", input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")

        return await self.arun_child_validation(data)

    async def ato_representation(self, value: dict):
        result = {}
        for key, val in value.items():
            if hasattr(self.child, "ato_representation"):
                result[key] = await self.child.ato_representation(val)
            else:
                result[key] = self.child.to_representation(val)

        return {str(key): self.child.ato_representation(val) if val is not None else None for key, val in value.items()}

    async def arun_child_validation(self, data):
        result = {}
        errors = {}

        for key, value in data.items():
            key = str(key)

            try:
                if hasattr(self.child, "arun_validation"):
                    result[key] = await self.child.arun_validation(value)
                else:
                    result[key] = self.child.run_validation(value)
            except ValidationError as e:
                errors[key] = e.detail

        if not errors:
            return result
        raise ValidationError(errors)


class HStoreField(DRFHStoreField, DictField):
    pass


class JSONField(DRFJSONField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)


class ReadOnlyField(DRFReadOnlyField, AsyncField):
    async def ato_representation(self, value):
        return self.to_representation(value)


class HiddenField(DRFHiddenField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)


class SerializerMethodField(DRFSerializerMethodField, AsyncField):
    async def ato_representation(self, attribute):
        method = getattr(self.parent, self.method_name)
        if inspect.iscoroutinefunction(method):
            return await method(attribute)
        return method(attribute)


class ModelField(DRFModelField, AsyncField):
    async def ato_internal_value(self, data):
        return self.to_internal_value(data)

    async def ato_representation(self, value):
        return self.to_representation(value)

    async def aget_attribute(self, instance):
        return instance
