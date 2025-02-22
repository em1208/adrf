import contextlib
import sys
from urllib import parse

from async_property import async_property
from django.core.exceptions import ObjectDoesNotExist
from django.urls import get_script_prefix
from django.urls import resolve
from django.urls import Resolver404
from django.utils.encoding import smart_str
from django.utils.encoding import uri_to_iri
from rest_framework.fields import SkipField
from rest_framework.relations import empty
from rest_framework.relations import HyperlinkedIdentityField as DRFHyperlinkedIdentityField
from rest_framework.relations import HyperlinkedRelatedField as DRFHyperlinkedRelatedField
from rest_framework.relations import is_simple_callable
from rest_framework.relations import iter_options
from rest_framework.relations import MANY_RELATION_KWARGS
from rest_framework.relations import ManyRelatedField as DRFManyRelatedField
from rest_framework.relations import ObjectTypeError
from rest_framework.relations import ObjectValueError
from rest_framework.relations import PKOnlyObject
from rest_framework.relations import PrimaryKeyRelatedField as DRFPrimaryKeyRelatedField
from rest_framework.relations import RelatedField as DRFRelatedField
from rest_framework.relations import SlugRelatedField as DRFSlugRelatedField
from rest_framework.relations import StringRelatedField as DRFStringRelatedField

from adrf.fields import AsyncField
from adrf.utils import aget_attribute
from adrf.utils import async_attrgetter
from adrf.utils import is_async_callable


class RelatedField(DRFRelatedField, AsyncField):
    queryset = None
    html_cutoff = None
    html_cutoff_text = None

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        This method handles creating a parent `ManyRelatedField` instance
        when the `many=True` keyword argument is passed.

        Typically you won't need to override this method.

        Note that we're over-cautious in passing most arguments to both parent
        and child classes in order to try to cover the general case. If you're
        overriding this method you'll probably want something much simpler, eg:

        @classmethod
        def many_init(cls, *args, **kwargs):
            kwargs['child'] = cls()
            return CustomManyRelatedField(*args, **kwargs)
        """
        list_kwargs = {"child_relation": cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyRelatedField(**list_kwargs)

    async def aget_attribute(self, instance):
        if self.use_pk_only_optimization() and self.source_attrs:
            # Optimized case, return a mock object only containing the pk attribute.
            with contextlib.suppress(AttributeError):
                attribute_instance = await aget_attribute(instance, self.source_attrs[:-1])
                value = attribute_instance.serializable_value(self.source_attrs[-1])
                if is_async_callable(value):
                    # Handle edge case where the relationship `source` argument
                    # points to a `get_relationship()` method on the model.
                    value = await value()
                if is_simple_callable(value):
                    # Handle edge case where the relationship `source` argument
                    # points to a `get_relationship()` method on the model.
                    value = value()

                # Handle edge case where relationship `source` argument points
                # to an instance instead of a pk (e.g., a `@property`).
                value = getattr(value, "pk", value)

                return PKOnlyObject(pk=value)
        # Standard case, return the object instance.
        return await super().aget_attribute(instance)

    async def arun_validation(self, data=empty):
        # We force empty strings to None values for relational fields.
        if data == "":
            data = None
        return await super().arun_validation(data)

    async def aget_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return {self.ato_representation(item): self.display_value(item) async for item in queryset}

    @async_property
    async def choices(self):
        return await self.aget_choices()

    @async_property
    async def grouped_choices(self):
        return await self.choices

    async def aiter_options(self):
        choices = await self.aget_choices(cutoff=self.html_cutoff)
        return iter_options(choices, cutoff=self.html_cutoff, cutoff_text=self.html_cutoff_text)


class StringRelatedField(DRFStringRelatedField, RelatedField):
    async def ato_representation(self, value):
        return self.to_representation(value)


class PrimaryKeyRelatedField(DRFPrimaryKeyRelatedField, RelatedField):
    async def ato_internal_value(self, data):
        if self.pk_field is not None:
            if hasattr(self.pk_field, "ato_internal_value"):
                data = await self.pk_field.ato_internal_value(data)
            else:
                data = self.pk_field.to_internal_value(data)
        queryset = self.get_queryset()
        try:
            if isinstance(data, bool):
                raise TypeError
            return await queryset.aget(pk=data)
        except ObjectDoesNotExist:
            self.fail("does_not_exist", pk_value=data)
        except (TypeError, ValueError):
            self.fail("incorrect_type", data_type=type(data).__name__)

    async def ato_representation(self, value):
        if self.pk_field is not None:
            if hasattr(self.pk_field, "ato_representation"):
                return await self.pk_field.ato_representation(value.pk)
            return self.pk_field.to_representation(value.pk)
        return value.pk


class HyperlinkedRelatedField(DRFHyperlinkedRelatedField, RelatedField):
    async def aget_object(self, view_name, view_args, view_kwargs):
        """
        Return the object corresponding to a matched URL.

        Takes the matched URL conf arguments, and should return an
        object instance, or raise an `ObjectDoesNotExist` exception.
        """
        lookup_value = view_kwargs[self.lookup_url_kwarg]
        lookup_kwargs = {self.lookup_field: lookup_value}
        queryset = self.get_queryset()

        try:
            return await queryset.aget(**lookup_kwargs)
        except ValueError:
            exc = ObjectValueError(str(sys.exc_info()[1]))
            raise exc.with_traceback(sys.exc_info()[2])
        except TypeError:
            exc = ObjectTypeError(str(sys.exc_info()[1]))
            raise exc.with_traceback(sys.exc_info()[2])

    async def ato_internal_value(self, data):
        request = self.context.get("request")
        try:
            http_prefix = data.startswith(("http:", "https:"))
        except AttributeError:
            self.fail("incorrect_type", data_type=type(data).__name__)

        if http_prefix:
            # If needed convert absolute URLs to relative path
            data = parse.urlparse(data).path
            prefix = get_script_prefix()
            if data.startswith(prefix):
                data = "/" + data[len(prefix) :]

        data = uri_to_iri(parse.unquote(data))

        try:
            match = resolve(data)
        except Resolver404:
            self.fail("no_match")

        try:
            expected_viewname = request.versioning_scheme.get_versioned_viewname(self.view_name, request)
        except AttributeError:
            expected_viewname = self.view_name

        if match.view_name != expected_viewname:
            self.fail("incorrect_match")

        try:
            return await self.aget_object(match.view_name, match.args, match.kwargs)
        except (ObjectDoesNotExist, ObjectValueError, ObjectTypeError):
            self.fail("does_not_exist")

    async def ato_representation(self, value):
        return self.to_representation(value)


class HyperlinkedIdentityField(DRFHyperlinkedIdentityField, HyperlinkedRelatedField):
    pass


class SlugRelatedField(DRFSlugRelatedField, RelatedField):
    async def ato_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return await queryset.aget(**{self.slug_field: data})
        except ObjectDoesNotExist:
            self.fail("does_not_exist", slug_name=self.slug_field, value=smart_str(data))
        except (TypeError, ValueError):
            self.fail("invalid")

    async def ato_representation(self, obj):
        slug = self.slug_field
        if "__" in slug:
            # handling nested relationship if defined
            slug = slug.replace("__", ".")
        return await async_attrgetter(slug)(obj)


class ManyRelatedField(DRFManyRelatedField, AsyncField):
    async def ato_internal_value(self, data):
        if isinstance(data, str) or not hasattr(data, "__iter__"):
            self.fail("not_a_list", input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")

        result = []
        for item in data:
            if hasattr(self.child_relation, "ato_internal_value"):
                result.append(await self.child_relation.ato_internal_value(item))
            else:
                result.append(self.child_relation.to_internal_value(item))
        return result

    async def aget_attribute(self, instance):
        # Can't have any relationships if not created
        if hasattr(instance, "pk") and instance.pk is None:
            return []

        try:
            relationship = await aget_attribute(instance, self.source_attrs)
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

        return relationship.all() if hasattr(relationship, "all") else relationship

    async def ato_representation(self, iterable):
        result = []
        if hasattr(iterable, '__aiter__'):
            async for value in iterable:
                if hasattr(self.child_relation, "ato_representation"):
                    result.append(await self.child_relation.ato_representation(value))
                else:
                    result.append(self.child_relation.to_representation(value))
        else:
            for value in iterable:
                if hasattr(self.child_relation, "ato_representation"):
                    result.append(await self.child_relation.ato_representation(value))
                else:
                    result.append(self.child_relation.to_representation(value))
        return result

    async def aget_choices(self, cutoff=None):
        if hasattr(self.child_relation, "aget_choices"):
            return await self.child_relation.aget_choices(cutoff)
        return self.child_relation.get_choices(cutoff)

    @async_property
    async def choices(self):
        return await self.aget_choices()

    @async_property
    async def grouped_choices(self):
        return await self.choices

    async def aiter_options(self):
        choices = await self.get_choices(cutoff=self.html_cutoff)
        return iter_options(choices, cutoff=self.html_cutoff, cutoff_text=self.html_cutoff_text)
