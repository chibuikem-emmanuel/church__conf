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
    """
    Handles sending a broadcast email to all attendees of a specific conference
    using the Brevo (Sendinblue) API v3.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    attendees = conference.attendee_set.all()

    if request.method == "POST":
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')
        
        # Get list of attendee emails
        email_list = list(attendees.values_list('email', flat=True))

        if not email_list:
            messages.warning(request, "No attendees registered for this conference.")
            return redirect('attendee_list', conf_id=conf_id)

        # 1. Configure Brevo API Key
        configuration = sib_api_v3_sdk.Configuration()
        # Ensure 'BREVO_PASSWORD' in Render contains your xkeysib- API key
        configuration.api_key['api-key'] = settings.EMAIL_HOST_PASSWORD 

        api_client = sib_api_v3_sdk.ApiClient(configuration)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

        # 2. Prepare the Email Payload
        # Sender must be a verified email in your Brevo account
        sender = {"name": "Confy", "email": "chizaramchibuikem@gmail.com"}
        
        # We send 'To' the admin and 'BCC' all attendees for privacy
        to = [{"email": "chizaramchibuikem@gmail.com"}]
        bcc_list = [{"email": email} for email in email_list]
        
        # Wrap message in basic HTML for better delivery
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #4f46e5; border-bottom: 2px solid #4f46e5; padding-bottom: 10px;">
                        {conference.title} - Update
                    </h2>
                    <p style="white-space: pre-wrap;">{message_body}</p>
                    <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                        You are receiving this because you registered for {conference.title}.
                    </div>
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
            # 3. Execute the Send (Method name: send_transac_email)
            api_response = api_instance.send_transac_email(send_smtp_email)
            print(f"BREVO SUCCESS: {api_response}")
            
            messages.success(request, f"Broadcast successfully sent to {len(email_list)} attendees!")
            return redirect('attendee_list', conf_id=conf_id)
        
        except ApiException as e:
            # Logs detailed error if API key is invalid or quota is hit
            print(f"BREVO API ERROR: {e}")
            messages.error(request, f"Mail System Error: {e.reason}")
            
            # Return to form with existing data so user doesn't lose their progress
            return render(request, 'compose_email.html', {
                'conference': conference,
                'attendees': attendees,
                'subject': subject,
                'message': message_body
            })

    # GET request: Show the empty form
    return render(request, 'compose_email.html', {
        'conference': conference, 
        'attendees': attendees
    })