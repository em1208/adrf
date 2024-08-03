from django.http import Http404
from django.test import TestCase

from adrf.shortcuts import aget_object_or_404

from .models import User


class TestAGetObject(TestCase):
    async def test_aget_object_or_404_not_a_model_raises(self):
        with self.assertRaises(ValueError):
            await aget_object_or_404(None, id=1)

    async def test_aget_object_or_404_raises(self):
        with self.assertRaises(Http404):
            await aget_object_or_404(User, id=1)

    async def test_aget_object_or_404_with_model_succeeds(self):
        username = "test"
        user = await User.objects.acreate(username=username)
        obj = await aget_object_or_404(User, username=username)
        assert user == obj

    async def test_aget_object_or_404_with_queryset_succeeds(self):
        username = "test"
        user = await User.objects.acreate(username=username)
        obj = await aget_object_or_404(User.objects.all(), username=username)
        assert user == obj
