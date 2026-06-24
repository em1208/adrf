from django.contrib.auth.models import User
from django.db import models


class Order(models.Model):
    name = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class ModelA(models.Model):
    name = models.TextField()


class ModelB(models.Model):
    fielda = models.ForeignKey(ModelA, on_delete=models.CASCADE)


class Parent(models.Model):
    name = models.CharField(default="foo")
    description = models.CharField(default="bar")

    @property
    async def custom_name(self):
        return self.name

    @property
    async def custom_description(self):
        return self.description


class Child(models.Model):
    name = models.CharField(default="foo")
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)

    @property
    async def custom_name(self):
        return self.name

    @property
    async def custom_parent(self):
        return self.parent