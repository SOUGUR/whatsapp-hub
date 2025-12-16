
from django.urls import path
from whatsapphub.webhooks.twilio import twilio_status_callback
from whatsapphub.views import (
    BulkWhatsAppSendView,
    TemplateCreateView,
    TemplateSubmitForApprovalView,
    TemplateApprovalStatusView
)

urlpatterns = [
    path("bulk-send/", BulkWhatsAppSendView.as_view()),
    path("webhooks/twilio/status/", twilio_status_callback),
    path("templates/", TemplateCreateView.as_view()),
    path("templates/<int:template_id>/submit/", TemplateSubmitForApprovalView.as_view()),
    path("templates/<int:template_id>/approval-status/",TemplateApprovalStatusView.as_view()),
]