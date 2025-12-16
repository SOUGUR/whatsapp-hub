import redis
from django.conf import settings

class RateLimiter:
    def __init__(self, max_requests=50, window=3600):
        self.redis = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.max_requests = max_requests
        self.window = window

    def allow(self, identifier):
        key = f"wa_rate:{identifier}"
        count = self.redis.incr(key)

        if count == 1:
            self.redis.expire(key, self.window)

        return count <= self.max_requests
