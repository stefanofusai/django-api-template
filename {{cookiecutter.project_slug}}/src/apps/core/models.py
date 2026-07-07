import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CreatedAtModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class CreatedAtUpdatedAtModel(CreatedAtModel):
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    # uuid7 (stdlib since 3.14) over uuid4: time-ordered values keep b-tree
    # primary-key indexes append-mostly instead of randomly fragmented.
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    class Meta:
        abstract = True


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)

    class Meta:
        ordering = ("username",)
        verbose_name = AbstractUser.Meta.verbose_name
        verbose_name_plural = AbstractUser.Meta.verbose_name_plural
