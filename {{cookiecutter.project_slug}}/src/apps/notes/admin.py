from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Note


@admin.register(Note)
class NoteAdmin(ModelAdmin):
    list_display = ("created_at", "updated_at", "owner", "title")
