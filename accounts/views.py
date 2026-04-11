from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegisterForm, ChurchForm

def register(request):
    user_form = RegisterForm(request.POST or None)
    church_form = ChurchForm(request.POST or None)

    if user_form.is_valid() and church_form.is_valid():
        user = user_form.save(commit=False)
        user.set_password(user.password)
        user.save()

        church = church_form.save(commit=False)
        church.user = user
        church.save()

        login(request, user)
        return redirect('dashboard')

    return render(request, 'register.html', {
        'user_form': user_form,
        'church_form': church_form
    })