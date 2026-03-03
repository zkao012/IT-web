from django.conf import settings
from django.db import models

class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # 对应你们“Session/Progress”核心字段（简化版）
    title = models.CharField(max_length=128)              # 可先当 task/session 的标题
    planned_start = models.DateTimeField(null=True, blank=True)
    planned_end = models.DateTimeField(null=True, blank=True)

    actual_minutes = models.PositiveIntegerField(default=0)
    completion_percent = models.PositiveIntegerField(default=0)  # 0-100
    status = models.CharField(max_length=32, default="planned")  # planned/doing/done
    notes = models.CharField(max_length=256, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.completion_percent}%)"
