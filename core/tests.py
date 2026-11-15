from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

LOCMEM_CACHE = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'ratelimit-tests'}}


@override_settings(RATELIMIT_ENABLED=True, RATELIMIT_GLOBAL_PER_MINUTE=1000, CACHES=LOCMEM_CACHE)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_login_bruteforce_blocked(self):
        url = reverse('users:login')
        data = {'username': 'hacker', 'password': 'wrong'}
        # 5 спроб дозволено
        for _ in range(5):
            self.assertEqual(self.client.post(url, data).status_code, 200)
        # 6-та вже блокується
        self.assertEqual(self.client.post(url, data).status_code, 429)

    def test_get_requests_not_limited_by_login_limit(self):
        url = reverse('users:login')
        for _ in range(10):
            self.assertEqual(self.client.get(url).status_code, 200)

    @override_settings(RATELIMIT_GLOBAL_PER_MINUTE=3)
    def test_global_limit(self):
        url = reverse('catalog:home')
        for _ in range(3):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 429)


class ErrorPagesTests(TestCase):
    def test_404_page(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
