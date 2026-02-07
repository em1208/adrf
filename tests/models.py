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
