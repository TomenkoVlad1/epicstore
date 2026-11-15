from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalog.models import Product
from library.models import LibraryItem
from users.models import CustomUser


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user('buyer', 'buyer@test.com', 'StrongPass123!')
        self.client.force_login(self.user)
        self.paid = Product.objects.create(title='Paid', slug='paid', price=Decimal('20.00'))
        self.free = Product.objects.create(title='Free', slug='free', price=Decimal('0'))

    def add(self, product):
        return self.client.post(reverse('cart:cart_add', args=[product.id]))

    def set_balance(self, amount):
        self.user.profile.balance = Decimal(amount)
        self.user.profile.save()

    def test_add_to_cart(self):
        self.add(self.paid)
        self.assertEqual(self.client.session['cart'], [self.paid.id])

    def test_add_same_game_twice(self):
        self.add(self.paid)
        self.add(self.paid)
        self.assertEqual(self.client.session['cart'], [self.paid.id])

    def test_cart_add_requires_post(self):
        response = self.client.get(reverse('cart:cart_add', args=[self.paid.id]))
        self.assertEqual(response.status_code, 405)

    def test_free_game_checkout(self):
        self.add(self.free)
        response = self.client.post(reverse('cart:checkout'))
        self.assertRedirects(response, reverse('cart:thank_you'))
        self.assertTrue(LibraryItem.objects.filter(user=self.user, product=self.free).exists())

    def test_not_enough_money_redirects_to_balance(self):
        self.set_balance('5.00')
        self.add(self.paid)
        response = self.client.post(reverse('cart:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('users:balance')))
        self.assertIn('need=15.00', response.url)
        # нічого не куплено і гроші не списані
        self.assertFalse(LibraryItem.objects.exists())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal('5.00'))

    def test_paid_checkout_takes_money(self):
        self.set_balance('50.00')
        self.add(self.paid)
        self.client.post(reverse('cart:checkout'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal('30.00'))
        item = LibraryItem.objects.get(user=self.user, product=self.paid)
        self.assertEqual(item.price_paid, Decimal('20.00'))
        # кошик після покупки порожній
        self.assertEqual(self.client.session.get('cart', []), [])

    def test_cannot_add_owned_game(self):
        LibraryItem.objects.create(user=self.user, product=self.paid)
        self.add(self.paid)
        self.assertEqual(self.client.session.get('cart', []), [])

    def test_checkout_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('cart:checkout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)
