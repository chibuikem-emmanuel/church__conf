from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
import requests

from .models import Conference, Attendee
from .forms import ConferenceForm, AttendeeForm

from openpyxl import Workbook
import qrcode
from io import BytesIO


# ================= AUTH =================

def user_login(request):
    if request.method == "POST":
        user = authenticate(
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials")
    return render(request, 'login.html')


def user_logout(request):
    if request.method == "POST":
        logout(request)
    return redirect('login')


# ================= HOME =================

def home(request):
    return render(request, 'home.html')


# ================= DASHBOARD =================

@login_required
def dashboard(request):
    church = request.user.church
    conferences = Conference.objects.filter(church=church)
    return render(request, 'dashboard.html', {'conferences': conferences})


# ================= CONFERENCE =================

@login_required
def create_conference(request):
    form = ConferenceForm(request.POST or None)
    if form.is_valid():
        conf = form.save(commit=False)
        conf.church = request.user.church
        conf.save()
        return redirect('dashboard')
    return render(request, 'create_conference.html', {'form': form})


@login_required
def delete_conference(request, pk):
    conf = get_object_or_404(Conference, id=pk, church=request.user.church)
    if request.method == "POST":
        conf.delete()
    return redirect('dashboard')


# ================= EVENT REGISTRATION =================

def event_page(request, pk):
    conference = Conference.objects.get(pk=pk)

    if request.method == "POST":
        form = AttendeeForm(request.POST)

        if form.is_valid():
            attendee = form.save(commit=False)
            attendee.conference = conference

            if Attendee.objects.filter(
                conference=conference,
                email=attendee.email
            ).exists():
                return render(request, 'event_page.html', {
                    'form': form,
                    'conference': conference,
                    'error': 'You already registered'
                })

            attendee.save()

            # ✅ STORE SUCCESS IN SESSION
            request.session['registration_success'] = True

            return redirect('event_page', pk=pk)

    else:
        form = AttendeeForm()

    # ✅ CHECK SUCCESS FLAG
    success = None
    if request.session.pop('registration_success', False):
        success = "Registration successful"

    return render(request, 'event_page.html', {
        'form': form,
        'conference': conference,
        'success': success
    })


# ================= ATTENDEES =================

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


@login_required
def delete_attendee(request, pk):
    attendee = get_object_or_404(Attendee, id=pk)
    if request.method == "POST":
        attendee.delete()
        messages.success(request, "Attendee deleted")
    return redirect(request.META.get('HTTP_REFERER'))


# ================= EXPORT =================

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


# ================= QR =================

def generate_qr(request, pk):
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    url = f"{base_url}/event/{pk}/"

    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')

    return HttpResponse(buffer.getvalue(), content_type="image/png")


# ==================================================
# BROADCAST EMAIL
# ==================================================
@login_required
def send_conference_broadcast(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    attendees = Attendee.objects.filter(conference=conference)

    if request.method == "POST":
        subject = request.POST.get("subject")
        body = request.POST.get("message")

        emails = list(
            attendees.exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )

        if not emails:
            messages.warning(request, "No attendee emails found.")
            return redirect("attendee_list", pk=conference.id)

        sent = 0
        failed = 0

        for email in emails:
            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False
                )
                sent += 1
            except Exception as e:
                failed += 1

        messages.success(
            request,
            f"Broadcast completed. Sent: {sent}, Failed: {failed}"
        )

        return redirect("attendee_list", pk=conference.id)

    return render(request, "compose_email.html", {
        "conference": conference,
        "attendees": attendees
    })






@login_required
def send_bulk_sms(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    attendees = Attendee.objects.filter(conference=conference)

    if request.method == "POST":
        message_text = request.POST.get("message")

        sent = 0
        failed = 0
        used_numbers = set()

        for attendee in attendees:

            if not attendee.phone:
                continue

            phone = attendee.phone.strip()

            # remove spaces only first
            phone = phone.replace(" ", "").replace("-", "")

            # Handle +234xxxxxxxxxx
            if phone.startswith("+234"):
                phone = phone.replace("+", "")

            # Handle 234xxxxxxxxxx
            elif phone.startswith("234"):
                pass

            # Handle 080xxxxxxxx
            elif phone.startswith("0"):
                phone = "234" + phone[1:]

            else:
                failed += 1
                continue

            # Must be 13 digits total
            if len(phone) != 13:
                failed += 1
                continue

            # Remove duplicates
            if phone in used_numbers:
                continue

            used_numbers.add(phone)

            payload = {
                "to": phone,
                "from": settings.TERMII_SENDER_ID,
                "sms": message_text,
                "type": "plain",
                "channel": "generic",
                "api_key": settings.TERMII_API_KEY
            }

            try:
                response = requests.post(
                    "https://api.ng.termii.com/api/sms/send",
                    json=payload,
                    timeout=15
                )

                if response.status_code == 200:
                    sent += 1
                else:
                    failed += 1

            except Exception:
                failed += 1

        messages.success(
            request,
            f"SMS sent successfully to {sent} attendees. Failed: {failed}"
        )

        return redirect("attendee_list", pk=conference.id)

    return render(request, "send_sms.html", {
        "conference": conference,
        "attendees": attendees
    })
