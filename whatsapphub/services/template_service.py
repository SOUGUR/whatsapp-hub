from twilio.rest import Client
from django.conf import settings
import requests
import base64

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


class WhatsAppTemplateService:
    BASE_URL = "https://content.twilio.com/v1/Content"

    @staticmethod
    def _auth_header():
        credentials = f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    @classmethod
    def create_draft(cls, payload):
        response = requests.post(
            cls.BASE_URL,
            json=payload,
            headers=cls._auth_header(),
            timeout=15,
        )

        if response.status_code not in (200, 201):
            raise Exception(
                f"Twilio Content API error: {response.status_code} {response.text}"
            )

        return response.json() 

    @staticmethod
    def update_draft(content_sid, body, variables):
        content = client.content.v1.contents(content_sid).update(
            variables=variables,
            types={
                "twilio/text": {
                    "body": body
                }
            }
        )
        return content.sid

    @classmethod
    def submit_for_whatsapp_approval(cls, content_sid, name, category):
        """
        Mirrors:
        POST /v1/Content/{SID}/ApprovalRequests/whatsapp
        """
        url = f"{cls.BASE_URL}/{content_sid}/ApprovalRequests/whatsapp"

        payload = {
            "name": name,
            "category": category
        }

        response = requests.post(
            url,
            json=payload,
            headers=cls._auth_header(),
            timeout=15
        )

        if response.status_code not in (200, 201):
            raise Exception(
                f"Twilio approval error: {response.status_code} {response.text}"
            )

        return response.json()
    

    @classmethod
    def get_approval_requests(cls, content_sid):
        """
        Mirrors:
        GET /v1/Content/{ContentSid}/ApprovalRequests
        """
        url = f"{cls.BASE_URL}/{content_sid}/ApprovalRequests"

        response = requests.get(
            url,
            headers=cls._auth_header(),
            timeout=15,
        )

        if response.status_code != 200:
            raise Exception(
                f"Twilio approval fetch error: {response.status_code} {response.text}"
            )

        return response.json()
    
    
    
