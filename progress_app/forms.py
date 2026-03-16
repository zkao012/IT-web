from django import forms
from booking_app.models import Task


class ProgressTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }