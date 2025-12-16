from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from whatsapphub.models import WhatsAppMessage

@csrf_exempt
def twilio_status_callback(request):
    print("===== TWILIO WEBHOOK DATA =================:", dict(request.POST))
    sid = request.POST.get("MessageSid")
    status = request.POST.get("MessageStatus")
    error_code = request.POST.get("ErrorCode")
    error_message = request.POST.get("ErrorMessage")

    try:
        msg = WhatsAppMessage.objects.get(sid=sid)
        msg.status = status
        msg.error_code = error_code
        msg.error_message = error_message
        msg.save(update_fields=["status", "error_code", "error_message"])
    except WhatsAppMessage.DoesNotExist:
        pass

    return HttpResponse(status=200)
