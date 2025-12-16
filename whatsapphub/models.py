from django.db import models

class WhatsAppMessage(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("read", "Read"),
        ("failed", "Failed"),
        ("undelivered", "Undelivered"),
    ]

    sid = models.CharField(max_length=64, unique=True, null=True, blank=True)

    to_number = models.CharField(max_length=20)
    template_sid = models.CharField(max_length=64)
    template_variables = models.JSONField(default=dict)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued"
    )

    error_code = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    client_reference = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.to_number} - {self.status}"


class WhatsAppTemplate(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(
        max_length=20,
        choices=[
            ("UTILITY", "Utility"),
            ("MARKETING", "Marketing"),
            ("AUTHENTICATION", "Authentication"),
        ],
    )

    content_sid = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True
    )

    body = models.TextField()
    variables = models.JSONField(default=dict)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    rejection_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)