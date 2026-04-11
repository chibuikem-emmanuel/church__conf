from django import forms
from .models import Conference, Attendee

class ConferenceForm(forms.ModelForm):
    class Meta:
        model = Conference
        fields = ['title', 'description']


class AttendeeForm(forms.ModelForm):
    class Meta:
        model = Attendee
        fields = ['name', 'email', 'phone', 'expectation']