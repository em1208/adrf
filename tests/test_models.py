from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
    name = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
