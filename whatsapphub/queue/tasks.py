from django.utils import timezone
from whatsapphub.models import WhatsAppMessage
from whatsapphub.services.sender import WhatsAppSender
from whatsapphub.services.rate_limiter import RateLimiter
from twilio.base.exceptions import TwilioRestException

sender = WhatsAppSender()
rate_limiter = RateLimiter()

def send_whatsapp_message(message_id):
    msg = WhatsAppMessage.objects.get(id=message_id)

    if msg.status in ("sent", "delivered", "read"):
        return

    if not rate_limiter.allow(msg.to_number):
        raise Exception("Rate limit exceeded")

    try:
        sid = sender.send_template(
            msg.to_number,
            msg.template_sid,
            msg.template_variables
        )

        msg.sid = sid
        msg.status = "sent"
        msg.sent_at = timezone.now()
        msg.save(update_fields=["sid", "status", "sent_at"])

    except TwilioRestException as e:
        print(f"==={e}=======")
        if e.code == 21656:
            msg.status = "failed"
            msg.error_code = str(e.code)
            msg.error_message = str(e)
            msg.save(update_fields=["status", "error_code", "error_message"])
            return  
        msg.status = "failed"
        msg.error_code = str(e.code)
        msg.error_message = str(e)
        msg.save(update_fields=["status", "error_code", "error_message"])
        raise  
    return sid
