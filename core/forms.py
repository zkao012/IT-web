from django import forms
from django.utils import timezone
from django.db.models import Sum
from .models import Session, Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'category', 'description', 'target_minutes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Read Django Docs'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: describe what you want to achieve'
            }),
            'target_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'e.g. 120'
            }),
        }
        labels = {
            'title': 'Task Title',
            'category': 'Category',
            'description': 'Description (optional)',
            'target_minutes': 'Target Minutes',
        }


class SessionBookForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['task', 'planned_start', 'planned_end', 'notes']
        widgets = {
            'task': forms.Select(attrs={
                'class': 'form-select'
            }),
            'planned_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'planned_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: add notes for this session...'
            }),
        }
        labels = {
            'task': 'Select Task',
            'planned_start': 'Start Time',
            'planned_end': 'End Time',
            'notes': 'Notes (optional)',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = user
        if user:
            self.fields['task'].queryset = user.tasks.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('planned_start')
        end = cleaned_data.get('planned_end')
        task = cleaned_data.get('task')

        if start and end:
            if end <= start:
                raise forms.ValidationError("End time must be after start time.")

            # 时间冲突检测
            if self.current_user:
                conflicts = Session.objects.filter(
                    user=self.current_user,
                    planned_start__lt=end,
                    planned_end__gt=start,
                ).exclude(status='cancelled')
                if self.instance.pk:
                    conflicts = conflicts.exclude(pk=self.instance.pk)
                if conflicts.exists():
                    raise forms.ValidationError(
                        "This time slot conflicts with an existing session."
                    )

        # 超额提示：用 in_progress + completed 的实际时长来判断（与 models 保持一致）
        if start and end and task:
            session_minutes = int((end - start).total_seconds() / 60)
            used_minutes = task.sessions.exclude(
                status__in=['cancelled', 'pending']
            ).aggregate(total=Sum('actual_minutes'))['total'] or 0
            remaining = task.target_minutes - used_minutes

            if remaining <= 0:
                raise forms.ValidationError(
                    f'"{task.title}" target already reached! '
                    f'Choose a different task or create a new one.'
                )

            if session_minutes > remaining:
                self.overtime_warning = (
                    f'Heads up: this session ({session_minutes} min) exceeds your '
                    f'remaining target ({remaining} min) for "{task.title}". '
                    f'Progress will be capped at 100%.'
                )

        return cleaned_data


class ProgressUpdateForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['actual_minutes', 'completion_percent', 'notes']
        widgets = {
            'actual_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'completion_percent': forms.NumberInput(attrs={
                'type': 'range',
                'class': 'form-range',
                'min': 0,
                'max': 100,
                'step': 5
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }