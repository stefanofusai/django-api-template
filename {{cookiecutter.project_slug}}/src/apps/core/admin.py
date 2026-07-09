{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from typing import TYPE_CHECKING

from django.contrib import admin, messages
{% else -%}
from django.contrib import admin
{% endif -%}
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
if TYPE_CHECKING:
    from django.forms import ModelForm
    from django.http import HttpRequest
{% endif %}

@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    form = UserChangeForm
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


@admin.register(Token)
class TokenAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "expires_at",
        "last_used_at",
        "name",
        "prefix",
        "revoked_at",
        "user",
    )
    list_select_related = ("user",)
    readonly_fields = ("created_at", "last_used_at", "prefix", "revoked_at")

    def get_fields(
        self, _request: HttpRequest, obj: Token | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            # Add form: never expose digest; issue() derives it.
            return ("name", "user", "expires_at")
        return (
            "name",
            "user",
            "expires_at",
            "prefix",
            "created_at",
            "last_used_at",
            "revoked_at",
        )

    def save_model(
        self,
        request: HttpRequest,
        obj: Token,
        form: ModelForm,
        change: bool,  # noqa: FBT001 -- Django's ModelAdmin.save_model contract
    ) -> None:
        if change:
            super().save_model(request, obj, form, change)
            return

        raw_token, issued = Token.issue(
            expires_at=form.cleaned_data.get("expires_at"),
            name=form.cleaned_data["name"],
            user=form.cleaned_data["user"],
        )
        obj.pk = issued.pk
        messages.warning(
            request,
            f"Copy this token now — it will not be shown again: {raw_token}",
        )
{%- endif %}
