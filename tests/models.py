import uuid

from django.contrib.auth.models import User
from django.db import models


class Order(models.Model):
    name = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class ModelA(models.Model):
    name = models.TextField()


class ModelB(models.Model):
    fielda = models.ForeignKey(ModelA, on_delete=models.CASCADE)


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()


class Parent(models.Model):
    name = models.CharField(max_length=100, default="foo-parent")
    description = models.CharField(max_length=100, default="bar-parent")

    @property
    async def custom_name(self):
        return f"custom-{self.name}"

    @property
    async def custom_description(self):
        return f"custom-{self.description}"


class Child(models.Model):
    name = models.CharField(max_length=100, default="foo-child")
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)

    @property
    async def custom_name(self):
        return f"custom-{self.name}"

    @property
    async def custom_parent(self):
        return self.parent
