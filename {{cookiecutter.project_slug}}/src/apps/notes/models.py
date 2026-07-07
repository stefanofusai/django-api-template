from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import CreatedAtUpdatedAtModel, UUIDModel


class Note(UUIDModel, CreatedAtUpdatedAtModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("owner"),
    )
    title = models.CharField(_("title"), max_length=255)
    body = models.TextField(_("body"), blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("note")
        verbose_name_plural = _("notes")

    def __str__(self) -> str:
        return self.title
