from django import forms
from .models import Progress


class ProgressForm(forms.ModelForm):
    class Meta:
        model = Progress
        fields = ["title", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"style": "width:360px;"}),
            "notes": forms.Textarea(attrs={"rows": 5, "style": "width:360px;"}),
        }