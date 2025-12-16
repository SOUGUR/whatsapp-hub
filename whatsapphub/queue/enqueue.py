from redis import Redis
# from rq import Queue
import django_rq
from rq import Retry
from django.conf import settings
from whatsapphub.queue.tasks import send_whatsapp_message
from whatsapphub.models import WhatsAppMessage

redis_conn = Redis.from_url(settings.REDIS_URL)
# queue = Queue("whatsapp", connection=redis_conn)
queue = django_rq.get_queue("whatsapp")

def enqueue_bulk_messages(messages):
    job_ids = []

    for data in messages:
        msg = WhatsAppMessage.objects.create(
            to_number=data["to"],
            template_sid=data["template_sid"],
            template_variables=data["variables"],
            client_reference=data.get("client_reference"),
            status="queued"
        )

        job = queue.enqueue(
            send_whatsapp_message,
            msg.id,
            retry=Retry(max=3, interval=[60, 120, 300])
        )

        job_ids.append(job.id)

    return job_ids
