from django.conf import settings
from django.db import models

class Progress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    completion_percent = models.PositiveIntegerField(default=0)  # 0-100
    completed = models.BooleanField(default=False)

    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
