{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
import hashlib
import secrets
{% endif -%}
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
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


class Token(models.Model):
    digest = models.CharField(_("digest"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=100)
    user = models.ForeignKey(
        User,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name=_("user"),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("token")
        verbose_name_plural = _("tokens")

    def __str__(self) -> str:
        return self.name

    @classmethod
    def issue(cls, *, name: str, user: User) -> tuple[str, Token]:
        raw_token = secrets.token_urlsafe(32)
        token = cls.objects.create(
            digest=cls.hash(raw_token),
            name=name,
            user=user,
        )
        return raw_token, token

    @staticmethod
    def hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
{%- endif %}
