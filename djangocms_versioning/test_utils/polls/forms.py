from django import forms

from .models import PollContent


class PollForm(forms.ModelForm):
    model = PollContent
