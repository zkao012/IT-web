from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Avg
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    @staticmethod
    def create_default_categories():
        defaults = [
            "Study",
            "Programming",
            "Revision",
            "Reading"
        ]

        for name in defaults:
            Category.objects.get_or_create(name=name)

    class Meta:
        verbose_name_plural = 'Categories'


class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=128)
    description = models.CharField(max_length=256, blank=True)
    target_minutes = models.IntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def total_actual_minutes(self):
        """Total minutes from in_progress and completed sessions"""
        return self.sessions.exclude(
            status__in=['cancelled', 'pending']
        ).aggregate(total=Sum('actual_minutes'))['total'] or 0

    def progress_percent(self):
        """Overall task progress based on time logged, capped at 100%"""
        if self.target_minutes == 0:
            return 0
        return min(int(self.total_actual_minutes() / self.target_minutes * 100), 100)

    def extra_minutes(self):
        """Minutes logged beyond the target, returns 0 if not exceeded"""
        extra = self.total_actual_minutes() - self.target_minutes
        return extra if extra > 0 else 0

    def average_quality(self):
        """Average completion percent across all valid sessions"""
        result = self.sessions.exclude(
            status__in=['cancelled', 'pending']
        ).exclude(
            completion_percent=0
        ).aggregate(avg=Avg('completion_percent'))['avg']
        return round(result) if result else 0

    def recent_streak(self):
        """Number of consecutive days with a session in the last 7 days"""
        now = timezone.now()
        streak = 0
        for i in range(7):
            day_start = (now - timezone.timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = (now - timezone.timedelta(days=i)).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            has_session = self.sessions.exclude(
                status__in=['cancelled', 'pending']
            ).filter(
                planned_start__gte=day_start,
                planned_start__lte=day_end,
            ).exists()
            if has_session:
                streak += 1
            else:
                break
        return streak

    def is_completed(self):
        """Returns True if task progress has reached or exceeded 100%"""
        return self.progress_percent() >= 100


class Session(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    planned_start = models.DateTimeField()
    planned_end = models.DateTimeField()
    actual_minutes = models.IntegerField(default=0)
    completion_percent = models.IntegerField(default=0)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    notes = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def planned_minutes(self):
        """Planned duration in minutes"""
        return int((self.planned_end - self.planned_start).total_seconds() / 60)

    def __str__(self):
        return f"{self.task.title} — {self.planned_start.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['planned_start']