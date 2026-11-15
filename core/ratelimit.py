"""
Простий rate limiting на кеші (Redis в продакшені).
Рахуємо скільки запитів зробив один IP за період, і якщо більше ліміту - 429.
"""
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string


def get_client_ip(request):
    # X-Forwarded-For можна довіряти тільки якщо перед сайтом стоїть наш проксі (nginx),
    # інакше хакер підставить туди будь-який IP і обійде ліміт
    if getattr(settings, 'RATELIMIT_TRUST_X_FORWARDED_FOR', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def hit(key, limit, period):
    """Додає один запит і повертає True, якщо ліміт перевищено."""
    # add спрацює тільки якщо ключа ще нема - так починається нове "вікно"
    if cache.add(key, 1, period):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        # ключ встиг протухнути між add та incr
        cache.set(key, 1, period)
        return False
    return count > limit


def too_many_requests(request):
    # рендеримо без request: глобальний ліміт спрацьовує ще до сесій,
    # і так сторінка не робить жодного запиту до бази
    response = HttpResponse(render_to_string('429.html'), status=429)
    response['Retry-After'] = '60'
    return response


def ratelimit(name, limit, period=60, methods=('POST',)):
    """
    Декоратор для в'юшок:
        @ratelimit('login', limit=5, period=60)
    = не більше 5 POST-запитів на хвилину з одного IP.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if settings.RATELIMIT_ENABLED and request.method in methods:
                key = f'rl:{name}:{get_client_ip(request)}'
                if hit(key, limit, period):
                    return too_many_requests(request)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
