from django.contrib import admin
from .models import Progress

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "completed", "completion_percent", "created_at")
    list_filter = ("completed",)
    search_fields = ("title", "notes")
