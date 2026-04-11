from django import forms
from django.contrib.auth.models import User
from .models import Church

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


class ChurchForm(forms.ModelForm):
    class Meta:
        model = Church
        fields = ['name', 'email']