from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .forms import RegisterForm, TopUpForm
from .models import CustomUser, UserProfile


def make_user(username='vlad', password='StrongPass123!', **kwargs):
    return CustomUser.objects.create_user(
        username=username, email=f'{username}@test.com', password=password, **kwargs
    )


class ProfileSignalTests(TestCase):
    def test_profile_created_automatically(self):
        user = make_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.balance, Decimal('0'))


class RegisterFormTests(TestCase):
    def form_data(self, **extra):
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'VeryStrong123!',
            'password2': 'VeryStrong123!',
            'country': 'Україна',
            'birth_date': '2005-05-20',
        }
        data.update(extra)
        return data

    def test_valid(self):
        self.assertTrue(RegisterForm(data=self.form_data()).is_valid())

    def test_birth_date_in_future_invalid(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        form = RegisterForm(data=self.form_data(birth_date=future))
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_email_must_be_unique(self):
        make_user('old')
        form = RegisterForm(data=self.form_data(email='old@test.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_register_view_saves_country_and_logs_in(self):
        response = self.client.post(reverse('users:register'), self.form_data())
        self.assertRedirects(response, reverse('catalog:home'))
        user = CustomUser.objects.get(username='newuser')
        self.assertEqual(user.profile.country, 'Україна')
        self.assertEqual(user.profile.birth_date, date(2005, 5, 20))
        # юзер одразу залогінений
        self.assertEqual(int(self.client.session['_auth_user_id']), user.id)


class TopUpTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_form_rejects_negative_and_zero(self):
        self.assertFalse(TopUpForm(data={'amount': '-5'}).is_valid())
        self.assertFalse(TopUpForm(data={'amount': '0'}).is_valid())
        self.assertTrue(TopUpForm(data={'amount': '12.50'}).is_valid())

    def test_top_up_adds_money_and_shows_success(self):
        response = self.client.post(reverse('users:balance'), {'amount': '25'}, follow=True)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal('25.00'))
        self.assertContains(response, 'Платіж успішний')

    def test_success_shown_only_once(self):
        self.client.post(reverse('users:balance'), {'amount': '5'})
        self.client.get(reverse('users:balance'))
        response = self.client.get(reverse('users:balance'))
        self.assertNotContains(response, 'Платіж успішний')


class ProfileViewTests(TestCase):
    def test_login_required(self):
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)

    def test_profile_page(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get(reverse('users:profile'))
        self.assertContains(response, user.username)
