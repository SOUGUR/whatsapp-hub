import json
from twilio.rest import Client
from django.conf import settings

class WhatsAppSender:
    def __init__(self):
        self.client = Client(   
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

        self.callback_url = settings.TWILIO_STATUS_CALLBACK_URL

    def send_template(self, to_number, template_sid, variables):
        message = self.client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{to_number}",
            content_sid=template_sid,
            content_variables=json.dumps(variables),
            # status_callback=self.callback_url
        )
        return message.sid
