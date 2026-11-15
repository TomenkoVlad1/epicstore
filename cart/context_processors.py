from .cart import Cart


def cart(request):
    # тепер змінна {{ cart }} є в усіх шаблонах (наприклад кількість біля іконки)
    return {'cart': Cart(request)}
