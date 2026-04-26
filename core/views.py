from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
from openpyxl import Workbook
import qrcode
from io import BytesIO

from .models import Conference, Attendee
from .forms import ConferenceForm, AttendeeForm

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


# ---------------- AUTH ----------------
def user_login(request):
    if request.method == "POST":
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('dashboard')
    return render(request, 'login.html')


def user_logout(request):
    if request.method == "POST":
        logout(request)
    return redirect('login')


# ---------------- HOME ----------------
def home(request):
    return render(request, 'home.html')


# ---------------- DASHBOARD ----------------
@login_required
def dashboard(request):
    conferences = Conference.objects.filter(church=request.user.church)
    return render(request, 'dashboard.html', {'conferences': conferences})


# ---------------- CREATE ----------------
@login_required
def create_conference(request):
    form = ConferenceForm(request.POST or None)
    if form.is_valid():
        conf = form.save(commit=False)
        conf.church = request.user.church
        conf.save()
        return redirect('dashboard')
    return render(request, 'create_conference.html', {'form': form})


# ---------------- PUBLIC REGISTRATION ----------------
def event_page(request, pk):
    conference = get_object_or_404(Conference, pk=pk)
    form = AttendeeForm(request.POST or None)

    if form.is_valid():
        attendee = form.save(commit=False)
        attendee.conference = conference

        # Prevent duplicate
        if Attendee.objects.filter(
            conference=conference
        ).filter(
            Q(email=attendee.email) | Q(phone=attendee.phone)
        ).exists():
            return render(request, 'event_page.html', {
                'form': form,
                'conference': conference,
                'error': 'You already registered'
            })

        attendee.save()

        return render(request, 'event_page.html', {
            'form': AttendeeForm(),
            'conference': conference,
            'success': 'Registration successful 🎉'
        })

    return render(request, 'event_page.html', {
        'form': form,
        'conference': conference
    })


# ---------------- ATTENDEE LIST ----------------
@login_required
def attendee_list(request, pk):
    conference = get_object_or_404(Conference, id=pk)
    query = request.GET.get('q')

    attendees = Attendee.objects.filter(conference=conference)

    if query:
        attendees = attendees.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    return render(request, 'attendee_list.html', {
        'attendees': attendees,
        'conference': conference
    })


# ---------------- DELETE ----------------
@login_required
def delete_conference(request, pk):
    conf = get_object_or_404(Conference, id=pk, church=request.user.church)
    if request.method == "POST":
        conf.delete()
    return redirect('dashboard')


@login_required
def delete_attendee(request, pk):
    attendee = get_object_or_404(Attendee, id=pk)
    if request.method == "POST":
        attendee.delete()
    return redirect(request.META.get('HTTP_REFERER'))


# ---------------- EXPORT EXCEL ----------------
@login_required
def export_attendees(request, pk):
    conference = get_object_or_404(Conference, id=pk)
    attendees = Attendee.objects.filter(conference=conference)

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendees"

    ws.append(['Name', 'Email', 'Phone', 'Expectation'])

    for a in attendees:
        ws.append([a.name, a.email, a.phone, a.expectation])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{conference.title}.xlsx"'

    wb.save(response)
    return response


# ---------------- QR ----------------
def generate_qr(request, pk):
    url = request.build_absolute_uri(f"/event/{pk}/")

    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')

    return HttpResponse(buffer.getvalue(), content_type="image/png")


# ---------------- BROADCAST EMAIL (BREVO) ----------------
@login_required
def send_conference_broadcast(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    attendees = conference.attendee_set.all()

    if request.method == "POST":
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')

        email_list = list(attendees.values_list('email', flat=True))

        if not email_list:
            messages.warning(request, "No attendees found.")
            return redirect('attendee_list', pk=conf_id)

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.EMAIL_HOST_PASSWORD

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        sender = {"name": "Confy", "email": settings.DEFAULT_FROM_EMAIL}
        to = [{"email": settings.DEFAULT_FROM_EMAIL}]
        bcc = [{"email": email} for email in email_list]

        html_content = f"""
        <h2>{conference.title} Update</h2>
        <p>{message_body}</p>
        """

        email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            bcc=bcc,
            html_content=html_content,
            sender=sender,
            subject=f"{conference.title} - {subject}"
        )

        try:
            api_instance.send_transac_email(email)
            messages.success(request, "Broadcast sent successfully ✅")
        except ApiException as e:
            messages.error(request, f"Error: {e}")

        return redirect('attendee_list', pk=conf_id)

    return render(request, 'compose_email.html', {
        'conference': conference,
        'attendees': attendees
    })
