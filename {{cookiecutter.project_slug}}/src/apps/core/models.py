import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class CreatedAtModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class CreatedAtUpdatedAtModel(CreatedAtModel):
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    class Meta:
        ordering = ("username",)
        verbose_name = AbstractUser.Meta.verbose_name
        verbose_name_plural = AbstractUser.Meta.verbose_name_plural


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    class Meta:
        abstract = True
