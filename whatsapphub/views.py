from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from whatsapphub.queue.enqueue import enqueue_bulk_messages

from whatsapphub.models import WhatsAppTemplate
from whatsapphub.services.template_service import WhatsAppTemplateService

class BulkWhatsAppSendView(APIView):
    def post(self, request):
        """
        Expected payload:
        {
          "messages": [
            {
              "to": "+919999999999",
              "template_sid": "HXxxxx",
              "variables": {"1": "Sourabh"},
              "client_reference": "order_123"
            }
          ]
        }
        """
        messages = request.data.get("messages", [])
        job_ids = enqueue_bulk_messages(messages)
        return Response(
            {"queued_jobs": job_ids},
            status=status.HTTP_202_ACCEPTED
        )


class TemplateCreateView(APIView):
    def post(self, request):
        """
        Expected payload (matches Twilio Content API):
        {
          "friendly_name": "owl_air_qr",
          "language": "en",
          "variables": {"1": "Owl Air Customer"},
          "types": {
            "twilio/quick-reply": {
              "body": "...",
              "actions": [...]
            },
            "twilio/text": {
              "body": "..."
            }
          }
        }
        """

        twilio_response = WhatsAppTemplateService.create_draft(request.data)

        template = WhatsAppTemplate.objects.create(
            name=request.data["friendly_name"],
            content_sid=twilio_response["sid"],
            body=request.data["types"]["twilio/text"]["body"],
            variables=request.data.get("variables", {}),
            status="draft",
        )

        return Response(
            {
                "id": template.id,
                "content_sid": template.content_sid,
                "twilio_status": twilio_response.get("status"),
            },
            status=status.HTTP_201_CREATED,
        )

    

class TemplateSubmitForApprovalView(APIView):
    def post(self, request, template_id):
        """
        POST /templates/{id}/submit/
        Body:
        {
          "category": "UTILITY"
        }
        """

        template = WhatsAppTemplate.objects.get(id=template_id)

        if template.status != "draft":
            return Response(
                {"error": "Template already submitted or finalized"},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = request.data.get("category")
        if category not in ("UTILITY", "MARKETING", "AUTHENTICATION"):
            return Response(
                {"error": "Invalid WhatsApp category"},
                status=status.HTTP_400_BAD_REQUEST
            )

        twilio_response = WhatsAppTemplateService.submit_for_whatsapp_approval(
            content_sid=template.content_sid,
            name=template.name,
            category=category,
        )

        template.status = "pending"
        template.save(update_fields=["status"])

        return Response(
            {
                "message": "Template submitted for WhatsApp approval",
                "twilio_response": twilio_response,
            },
            status=status.HTTP_200_OK
        )
    

class TemplateApprovalStatusView(APIView):
    """
    GET /templates/{id}/approval-status/
    """

    def get(self, request, template_id):
        template = WhatsAppTemplate.objects.get(id=template_id)

        if not template.content_sid:
            return Response(
                {"error": "Template has no content SID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        twilio_response = WhatsAppTemplateService.get_approval_requests(
            template.content_sid
        )

        # ---- Parse WhatsApp approval (important) ----
        approvals = twilio_response.get("approval_requests", [])

        whatsapp_approval = next(
            (
                a for a in approvals
                if a.get("channel") == "whatsapp"
            ),
            None
        )

        # ---- Sync local DB status ----
        if whatsapp_approval:
            approval_status = whatsapp_approval.get("status")

            if approval_status == "approved":
                template.status = "approved"
                template.rejection_reason = None
            elif approval_status == "rejected":
                template.status = "rejected"
                template.rejection_reason = whatsapp_approval.get(
                    "rejection_reason"
                )
            else:
                template.status = "pending"

            template.save(
                update_fields=["status", "rejection_reason"]
            )

        return Response(
            {
                "template_id": template.id,
                "content_sid": template.content_sid,
                "whatsapp_approval": whatsapp_approval,
            },
            status=status.HTTP_200_OK
        )
