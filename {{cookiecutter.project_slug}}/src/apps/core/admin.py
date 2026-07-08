from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}


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
        "user",
    )
    list_select_related = ("user",)
{%- endif %}
