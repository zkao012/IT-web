from django.contrib import admin
from .models import Progress

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "status", "completion_percent", "actual_minutes", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "user__username", "user__email")