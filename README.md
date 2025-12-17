# WhatsApp Hub – Twilio + Redis + RQ

WhatsApp Hub is a Django-based backend for sending bulk WhatsApp messages using the Twilio WhatsApp API, Redis, and RQ workers. It is designed as a production-style pipeline with rate limiting, retries, and database-backed message tracking for auditing and analytics.

## Architecture

The system follows this flow:

1. Client / Admin panel calls a bulk send endpoint (for example `POST /bulk-send`) with a list of phone numbers and message content.  
2. Django API enqueues one job per recipient into a Redis-backed RQ queue.  
3. RQ workers consume jobs, apply per-recipient rate limiting, and send messages via the Twilio WhatsApp API.  
4. Twilio returns a message SID immediately and later sends asynchronous status webhooks (queued, sent, delivered, read, failed, undelivered).  
5. A webhook endpoint updates the `WhatsAppMessage` table so the database is the source of truth for message history and status.

## Core components

- **Django backend** – Exposes REST endpoints for bulk send and Twilio webhooks, and defines the `WhatsAppMessage` model.
- **Redis + RQ** – Redis acts as the message broker, and RQ provides background job processing with retry policies and separate worker processes.[2][1]
- **Twilio WhatsApp integration** – A `WhatsAppSender` class wraps `twilio.rest.Client` to send WhatsApp messages from your Twilio WhatsApp-enabled number.[1]
- **Rate limiter** – A `RateLimiter` class uses Redis counters (keys like `rate:{phone}`) to enforce a maximum number of messages per window per recipient or user.[3][1]
- **Database model** – The `WhatsAppMessage` table stores content, recipient, Twilio SID, status, error codes, metadata, and timestamps for auditing and analytics.[1]

## Twilio WhatsApp setup

1. Create a Twilio account and enable WhatsApp in the Twilio console (sandbox or approved business sender).  
2. Note your `ACCOUNT_SID`, `AUTH_TOKEN`, and WhatsApp-enabled sender (for example `whatsapp:+14155238886`).  
3. Configure a Status Callback URL in Twilio for WhatsApp messages, pointing to your deployed webhook endpoint (for example `https://your-domain.com/webhooks/twilio/status/`).[1]

### WhatsApp sender

```python
from twilio.rest import Client

class WhatsAppSender:
    def __init__(self, account_sid, auth_token, from_number):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number  # e.g. "whatsapp:+14155238886"

    def send(self, to_number: str, message: str) -> str:
        msg = self.client.messages.create(
            from_=self.from_number,
            to=f"whatsapp:{to_number}",
            body=message,
        )
        return msg.sid
```

## Rate limiting

The rate limiter protects your Twilio account, WhatsApp spam rules, and your own infrastructure.[1]

```python
import redis

class RateLimiter:
    def __init__(self, max_requests=50, window=3600):
        self.redis = redis.Redis(decode_responses=True)
        self.max_requests = max_requests
        self.window = window

    def allow(self, key: str) -> bool:
        redis_key = f"rate:{key}"
        count = self.redis.incr(redis_key)
        if count == 1:
            self.redis.expire(redis_key, self.window)
        return count <= self.max_requests
```

Workers call `allow(to_number)` before sending; if it returns `False`, the job fails or is retried according to RQ’s retry configuration.[1]

## Message model and status tracking

The database is the authoritative record of what was sent and what happened to it.[1]

```python
from django.db import models

class WhatsAppMessage(models.Model):
    sid = models.CharField(max_length=64, unique=True, null=True)
    to_number = models.CharField(max_length=20)
    body = models.TextField()

    status = models.CharField(max_length=20, default="queued")
    error_code = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.to_number} - {self.status}"
```

### Twilio status webhook

Twilio calls your webhook to deliver status updates such as `queued`, `sent`, `delivered`, `read`, `failed`, and `undelivered`.[1]

```python
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import WhatsAppMessage

@csrf_exempt
def twilio_status_webhook(request):
    sid = request.POST.get("MessageSid")
    status = request.POST.get("MessageStatus")
    error_code = request.POST.get("ErrorCode")
    error_message = request.POST.get("ErrorMessage")

    try:
        msg = WhatsAppMessage.objects.get(sid=sid)
        msg.status = status
        msg.error_code = error_code
        msg.error_message = error_message
        msg.save()
    except WhatsAppMessage.DoesNotExist:
        pass

    return HttpResponse(status=200)
```

## Bulk enqueue and worker

Bulk sending is done by enqueuing one job per recipient into an RQ queue.[2][1]

```python
# whatsapphub/queue.py
from redis import Redis
from rq import Queue
from rq.retry import Retry
from whatsapphub.tasks import send_whatsapp_message

redis_conn = Redis()
queue = Queue("whatsapp", connection=redis_conn)

def enqueue_bulk_messages(phone_numbers, message):
    job_ids = []

    for number in phone_numbers:
        job = queue.enqueue(
            send_whatsapp_message,
            number,
            message,
            retry=Retry(max=3, interval=[60, 120, 300]),
        )
        job_ids.append(job.id)

    return job_ids
```

The worker task applies rate limiting, sends via Twilio, and updates the database.[1]

```python
# whatsapphub/tasks.py
from django.utils import timezone
from .sender import WhatsAppSender
from .rate_limiter import RateLimiter
from .models import WhatsAppMessage

sender = WhatsAppSender(account_sid, auth_token, from_number)
rate_limiter = RateLimiter()

def send_whatsapp_message(to_number, message):
    if not rate_limiter.allow(to_number):
        raise Exception("Rate limit exceeded")

    msg = WhatsAppMessage.objects.create(
        to_number=to_number,
        body=message,
        status="queued",
    )

    sid = sender.send(to_number, message)

    msg.sid = sid
    msg.status = "sent"
    msg.sent_at = timezone.now()
    msg.save()

    return sid
```

## Local development setup

1. **Clone the repository**

```bash
git clone https://github.com/SOUGUR/whatsapp-hub.git
cd whatsapp-hub
```

2. **Create and activate a virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```
[functions.get_full_page_content:1]

4. **Configure environment variables**

Create a `.env` file or export environment variables:

```bash
export TWILIO_ACCOUNT_SID="your_sid"
export TWILIO_AUTH_TOKEN="your_token"
export TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"
export REDIS_URL="redis://localhost:6379/0"
export DJANGO_SETTINGS_MODULE="whatsappcom.settings"
```

5. **Run migrations and start Django**

```bash
python manage.py migrate
python manage.py runserver
```

6. **Start Redis and RQ workers**

```bash
# Redis
redis-server

# In another terminal
rq worker whatsapp
```

Now you can hit your bulk-send endpoint (for example with Postman) using a payload like:[1]

```json
{
  "phone_numbers": ["+919999999999", "+918888888888"],
  "message": "Hello from WhatsApp Hub!"
}
```
