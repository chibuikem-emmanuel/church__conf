from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import logout
from django.core.mail import EmailMessage
from .models import Conference, Attendee, EmailTemplate
from .forms import ConferenceForm, AttendeeForm
from django.core.mail import send_mail
from django.http import HttpResponse
from openpyxl import Workbook
import qrcode
from io import BytesIO
from django.db.models import Q


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



@login_required
def dashboard(request):
    church = request.user.church
    conferences = Conference.objects.filter(church=church)
    return render(request, 'dashboard.html', {'conferences': conferences})


@login_required
def create_conference(request):
    form = ConferenceForm(request.POST or None)
    if form.is_valid():
        conf = form.save(commit=False)
        conf.church = request.user.church
        conf.save()
        return redirect('dashboard')
    return render(request, 'create_conference.html', {'form': form})


def event_page(request, pk):
    conference = Conference.objects.get(pk=pk)
    form = AttendeeForm(request.POST or None)

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

        return render(request, 'event_page.html', {
            'form': AttendeeForm(),
            'conference': conference,
            'success': 'Registration successful'
        })

    return render(request, 'event_page.html', {
        'form': form,
        'conference': conference
    })


@login_required
def attendee_list(request, pk):
    conference = Conference.objects.get(id=pk)
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



def delete_conference(request, pk):
    conf = get_object_or_404(Conference, id=pk, church=request.user.church)
    if request.method == "POST":
        conf.delete()
    return redirect('dashboard')

def delete_attendee(request, pk):
    attendee = get_object_or_404(Attendee, id=pk)
    if request.method == "POST":
        attendee.delete()
    return redirect(request.META.get('HTTP_REFERER'))



@login_required
def send_bulk_email(request, pk, template_id):
    conference = Conference.objects.get(pk=pk)
    template = EmailTemplate.objects.get(pk=template_id)

    attendees = Attendee.objects.filter(conference=conference)

    for a in attendees:
        message = template.body.replace("{{name}}", a.name)

        send_mail(
            template.subject,
            message,
            'your@gmail.com',
            [a.email]
        )

    return redirect('attendee_list', pk=pk)


@login_required
def export_attendees(request, pk):
    conference = Conference.objects.get(id=pk)
    attendees = Attendee.objects.filter(conference=conference)

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendees"

    # Header
    ws.append(['Name', 'Email', 'Phone', 'Expectation'])

    # Data
    for a in attendees:
        ws.append([a.name, a.email, a.phone, a.expectation])

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response['Content-Disposition'] = f'attachment; filename="{conference.title}.xlsx"'

    wb.save(response)

    return response





def home(request):
    return render(request, 'home.html')



def generate_qr(request, pk):
    url = f"https://the-confy.onrender.com/event/{pk}/"

    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format='PNG')

    return HttpResponse(buffer.getvalue(), content_type="image/png")



def send_conference_broadcast(request, conf_id):
    if request.method == "POST":
        conference = Conference.objects.get(id=conf_id)
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')
        
        # Get all email addresses for this conference
        emails = list(conference.attendees.values_list('email', flat=True))

        if emails:
            email = EmailMessage(
                subject=f"[{conference.title}] {subject}",
                body=message_body,
                from_email=None, # Uses DEFAULT_FROM_EMAIL
                to=[request.user.email], # Sends the main copy to the Admin
                bcc=emails, # Sends a blind copy to all attendees
            )
            email.send()
            
        return redirect('attendee_list', conf_id=conf_id)