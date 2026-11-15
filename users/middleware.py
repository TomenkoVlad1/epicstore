from datetime import timedelta

from django.utils import timezone

from .models import UserProfile


class LastSeenMiddleware:
    """Запам'ятовує коли юзер останній раз був на сайті - для статусу Online/Offline."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now()
            # пишемо в базу не частіше ніж раз на хвилину, щоб не навантажувати
            last = request.session.get('last_seen_saved')
            if not last or now.timestamp() - last > 60:
                UserProfile.objects.filter(user=request.user).update(last_seen=now)
                request.session['last_seen_saved'] = now.timestamp()

        return self.get_response(request)
