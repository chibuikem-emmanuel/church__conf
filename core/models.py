from django.db import models
from accounts.models import Church
import qrcode
from io import BytesIO
from django.core.files import File

class Conference(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        url = f"http://127.0.0.1:8000/event/{self.id}/"
        qr = qrcode.make(url)

        buffer = BytesIO()
        qr.save(buffer, format='PNG')

        self.qr_code.save(f'conf_{self.id}.png', File(buffer), save=False)
        super().save(*args, **kwargs)


class Attendee(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    expectation = models.TextField()


class EmailTemplate(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    body = models.TextField()