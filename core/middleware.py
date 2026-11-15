from django.conf import settings

from .ratelimit import get_client_ip, hit, too_many_requests


class GlobalRateLimitMiddleware:
    """
    Загальний ліміт на всі сторінки - захист від флуду / простого DDoS з одного IP.
    Статику і картинки не рахуємо.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.RATELIMIT_ENABLED and not request.path.startswith(('/static/', '/media/')):
            key = f'rl:global:{get_client_ip(request)}'
            if hit(key, settings.RATELIMIT_GLOBAL_PER_MINUTE, 60):
                return too_many_requests(request)
        return self.get_response(request)
