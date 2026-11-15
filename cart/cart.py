from catalog.models import Product

CART_SESSION_KEY = 'cart'


class Cart:
    """
    Кошик в сесії.
    Гру можна купити тільки один раз, тому кількість не потрібна -
    просто зберігаю список id ігор.
    """

    def __init__(self, request):
        self.session = request.session
        # тільки читаємо: порожній кошик в сесію не пишемо,
        # інакше для кожного відвідувача створювалась би сесія в базі
        self.cart = list(self.session.get(CART_SESSION_KEY, []))

    def save(self):
        self.session[CART_SESSION_KEY] = self.cart

    def add(self, product):
        if product.id not in self.cart:
            self.cart.append(product.id)
            self.save()

    def remove(self, product):
        if product.id in self.cart:
            self.cart.remove(product.id)
            self.save()

    def clear(self):
        self.cart = []
        self.session.pop(CART_SESSION_KEY, None)

    def get_products(self):
        return Product.objects.filter(id__in=self.cart, is_active=True).select_related('category')

    def get_total_price(self):
        return sum(p.final_price() for p in self.get_products())

    def __contains__(self, product):
        return product.id in self.cart

    def __len__(self):
        return len(self.cart)
