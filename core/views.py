from pyexpat.errors import messages
from django.contrib.messages import api as messages_api 
from django.contrib import messages
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

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Conference


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



# views.py







def send_conference_broadcast(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    attendees = conference.attendee_set.all()

    if request.method == "POST":
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')
        email_list = list(attendees.values_list('email', flat=True))

        if not email_list:
            messages.warning(request, "No attendees registered.")
            return redirect('attendee_list', conf_id=conf_id)

        # 1. Configure the Brevo API Key
        configuration = sib_api_v3_sdk.Configuration()
        # This uses the key you saved in your Render Environment Variables
        configuration.api_key['api-key'] = settings.EMAIL_HOST_PASSWORD 

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # 2. Prepare Email Data
        # We send it to the admin (you) and BCC the attendees for privacy
        sender = {"name": "Confy", "email": "chizaramchibuikem@gmail.com"}
        to = [{"email": "chizaramchibuikem@gmail.com"}]
        bcc_list = [{"email": email} for email in email_list]
        
        # Format the body as HTML
        html_content = f"""
        <html>
            <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
                    <h2 style="color: #4f46e5;">{conference.title}</h2>
                    <p>{message_body}</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <small style="color: #999;">Sent via Confy Management System</small>
                </div>
            </body>
        </html>
        """

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            bcc=bcc_list,
            html_content=html_content,
            sender=sender,
            subject=f"[{conference.title}] {subject}"
        )

        try:
            # 3. Send the request
            api_instance.send_trans_email(send_smtp_email)
            messages.success(request, f"Broadcast successfully sent via API to {len(email_list)} people!")
            return redirect('attendee_list', conf_id=conf_id)
        
        except ApiException as e:
            # Logs the exact error if Brevo rejects the request
            print(f"BREVO API ERROR: {e}")
            messages.error(request, f"Mail Error: {e.reason}")
            
            return render(request, 'compose_email.html', {
                'conference': conference,
                'attendees': attendees,
                'subject': subject,
                'message': message_body
            })

    return render(request, 'compose_email.html', {
        'conference': conference, 
        'attendees': attendees
    })