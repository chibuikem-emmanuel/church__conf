from django.contrib import admin
from .models import Conference, Attendee, EmailTemplate

admin.site.register(Conference)
admin.site.register(Attendee)
admin.site.register(EmailTemplate)