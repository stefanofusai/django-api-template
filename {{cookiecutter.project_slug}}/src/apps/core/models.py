{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
import hashlib
import secrets
{% endif -%}
import uuid
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from datetime import datetime
{% endif %}
from django.contrib.auth.models import AbstractUser
from django.db import models
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from django.utils import timezone
{% endif -%}
from django.utils.translation import gettext_lazy as _
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
TOKEN_PART_COUNT = 3
TOKEN_PREFIX = "pat"  # noqa: S105
TOKEN_PREFIX_BYTES = 6
TOKEN_SECRET_BYTES = 32
{% endif %}

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


class Token(CreatedAtModel):
    expires_at = models.DateTimeField(_("expires at"), blank=True, null=True)
    last_used_at = models.DateTimeField(_("last used at"), blank=True, null=True)
    user = models.ForeignKey(
        User,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name=_("user"),
    )
    digest = models.CharField(_("digest"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=100)
    prefix = models.CharField(_("prefix"), db_index=True, max_length=12)

    class Meta:
        ordering = ("name",)
        verbose_name = _("token")
        verbose_name_plural = _("tokens")

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def issue(
        cls, *, expires_at: datetime | None = None, name: str, user: User
    ) -> tuple[str, Token]:
        prefix = secrets.token_hex(TOKEN_PREFIX_BYTES)
        raw_token = (
            f"{TOKEN_PREFIX}_{prefix}_{secrets.token_urlsafe(TOKEN_SECRET_BYTES)}"
        )
        token = cls.objects.create(
            expires_at=expires_at,
            user=user,
            digest=cls.hash(raw_token),
            name=name,
            prefix=prefix,
        )
        return raw_token, token

    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    def mark_used(self) -> None:
        self.last_used_at = timezone.now()
        self.save(update_fields=("last_used_at",))

    @staticmethod
    def prefix_from(raw_token: str) -> str | None:
        parts = raw_token.split("_", 2)

        if len(parts) != TOKEN_PART_COUNT:
            return None

        token_prefix, prefix, secret = parts

        if token_prefix != TOKEN_PREFIX or not prefix or not secret:
            return None

        return prefix
{%- endif %}
