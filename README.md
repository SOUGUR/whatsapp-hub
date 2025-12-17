# WhatsApp Hub

Django-powered backend for bulk WhatsApp messaging with Twilio, Redis, and RQ.

## Overview

WhatsApp Hub provides a production-style messaging pipeline where a client or admin panel triggers bulk WhatsApp sends, and the system handles queuing, delivery, and status updates asynchronously. It is built to be a reusable backend component that can plug into dashboards, CRMs, or campaign tools that need reliable WhatsApp delivery at scale.

## Architecture

The flow starts when a client calls a bulk-send endpoint (for example `POST /bulk-send`) with a list of phone numbers and message content. The Django API enqueues one job per recipient into a Redis-backed RQ queue, workers send via Twilio's WhatsApp API, and Twilio webhooks update message status in the database so the DB becomes the source of truth.

### System Flow

1. Client / Admin panel calls a bulk send endpoint (for example `POST /bulk-send`) with a list of phone numbers and message content.
2. Django API enqueues one job per recipient into a Redis-backed RQ queue.
3. RQ workers consume jobs, apply per-recipient rate limiting, and send messages via the Twilio WhatsApp API.
4. Twilio returns a message SID immediately and later sends asynchronous status webhooks (queued, sent, delivered, read, failed, undelivered).
5. A webhook endpoint updates the `WhatsAppMessage` table so the database is the source of truth for auditing and analytics.

## Core Components

### Django Backend
Exposes REST endpoints for bulk sending and Twilio webhooks and defines the `WhatsAppMessage` model for persistence. This keeps all message metadata, status, and timestamps in one place for analytics and auditing.

### Redis + RQ Queue
Provide the background job pipeline, where Redis acts as the broker and RQ handles worker processes, retries, and queue separation for WhatsApp jobs.

### Twilio WhatsApp Integration
Wrapped in a `WhatsAppSender` class that uses `twilio.rest.Client` to send messages from a configured WhatsApp-enabled Twilio number.

### Rate Limiter
Uses a `RateLimiter` class backed by Redis counters (keys like `rate:{phone}`) to enforce a maximum number of messages per recipient per time window.

### Database Model
`WhatsAppMessage` tracks recipient, content, Twilio SID, status, error codes, metadata, and timestamps to give a complete lifecycle view for each message.

## Twilio WhatsApp Integration

### Configuration
The service assumes a Twilio WhatsApp-enabled account with configured `ACCOUNT_SID`, `AUTH_TOKEN`, and sender number such as `whatsapp:+14155238886`. Twilio is configured with a Status Callback URL pointing to the deployed webhook endpoint so every status transition (`queued`, `sent`, `delivered`, `read`, `failed`, `undelivered`) is reflected in the database.

### Webhook Handling
Every Twilio status update is received at a webhook endpoint, parsed, and immediately updates the corresponding `WhatsAppMessage` record with the latest status, error codes, and timestamps.

## Bulk Sending and Worker Execution

### Bulk Enqueue
Bulk sending is implemented by enqueuing one RQ job per recipient into a dedicated `whatsapp` queue. Each job carries the recipient phone number, message content, and metadata.

### Worker Tasks
Worker tasks apply rate limiting, create the initial `WhatsAppMessage` row, send via Twilio, and then update the record with the returned SID, status, and timestamps.

## Local Development Setup

### Prerequisites
- Python 3.8+
- Redis server
- Django
- Twilio account with WhatsApp enabled

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SOUGUR/whatsapp-hub.git
   cd whatsapp-hub
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   export TWILIO_ACCOUNT_SID=your_account_sid
   export TWILIO_AUTH_TOKEN=your_auth_token
   export TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   export REDIS_URL=redis://localhost:6379
   export DJANGO_SETTINGS_MODULE=whatsapphub.settings
   ```

5. **Run Django migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Start Redis:**
   ```bash
   redis-server
   ```

7. **Start Django development server:**
   ```bash
   python manage.py runserver
   ```

8. **Start RQ worker:**
   ```bash
   python manage.py rqworker whatsapp
   ```

## API Endpoints

### POST /bulk-send
Enqueue bulk WhatsApp messages for delivery.

**Request Body:**
```json
{
  "recipients": ["+1234567890", "+0987654321"],
  "message": "Your message content here",
  "metadata": {}
}
```

**Response:**
```json
{
  "queued": 2,
  "job_ids": ["job-id-1", "job-id-2"]
}
```

### POST /twilio-webhook
Twilio status callback endpoint. Automatically updates message status based on Twilio webhook data.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Twilio account ID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio authentication token | `authtoken` |
| `TWILIO_WHATSAPP_FROM` | WhatsApp-enabled Twilio number | `whatsapp:+14155238886` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `DJANGO_SETTINGS_MODULE` | Django settings module | `whatsapphub.settings` |

## Database Schema

### WhatsAppMessage Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Primary key |
| `recipient` | CharField | Phone number (E.164 format) |
| `message_content` | TextField | Message text |
| `twilio_sid` | CharField | Twilio message SID |
| `status` | CharField | Current status (queued, sent, delivered, read, failed, undelivered) |
| `error_code` | CharField | Twilio error code (if any) |
| `created_at` | DateTimeField | Message creation timestamp |
| `sent_at` | DateTimeField | Send timestamp |
| `delivered_at` | DateTimeField | Delivery timestamp |
| `read_at` | DateTimeField | Read timestamp |
| `metadata` | JSONField | Custom metadata |

## Production Deployment

### Docker
A `Dockerfile` is provided for containerized deployment. Build and run:

```bash
docker build -t whatsapp-hub .
docker run -e TWILIO_ACCOUNT_SID=... -e TWILIO_AUTH_TOKEN=... whatsapp-hub
```

### Scaling Workers
Deploy multiple RQ worker instances to handle increased message volume. Each worker connects to the same Redis queue.

## Security Considerations

- **Rate Limiting**: Prevents abuse by limiting messages per recipient per time window.
- **Database Encryption**: Store sensitive Twilio tokens in environment variables, never in code.
- **Webhook Verification**: Validate Twilio webhook signatures to ensure authenticity.
- **Access Control**: Implement authentication and authorization on all API endpoints.

## Error Handling and Retries

RQ provides automatic retry mechanisms. Failed jobs are logged and can be inspected via RQ dashboard or command-line tools. Twilio failures are recorded in the database for audit trails.

## Monitoring and Analytics

- Track message status distribution (sent, delivered, read, failed).
- Monitor queue depth and worker performance via RQ dashboard.
- Export message history and delivery reports from the database.

## Contributing

Contributions are welcome! Please follow PEP 8 style guidelines and include tests for new features.

## License

MIT License

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
