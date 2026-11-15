from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField('Назва', max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Категорія'
        verbose_name_plural = 'Категорії'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products',
        verbose_name='Категорія',
    )
    title = models.CharField('Назва', max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField('Опис', blank=True)
    developer = models.CharField('Розробник', max_length=100, blank=True)
    publisher = models.CharField('Видавець', max_length=100, blank=True)

    price = models.DecimalField('Ціна (USD)', max_digits=8, decimal_places=2, default=0)
    # якщо є знижка то ставимо сюди нову ціну
    discount_price = models.DecimalField(
        'Ціна зі знижкою', max_digits=8, decimal_places=2, null=True, blank=True
    )

    cover = models.ImageField('Обкладинка', upload_to='covers/', blank=True)
    # широка картинка для великого банера на сторінці "Цікавинки"
    banner = models.ImageField('Банер (широкий)', upload_to='banners/', blank=True)
    is_featured = models.BooleanField('Показувати в банері на головній', default=False)
    release_date = models.DateField('Дата виходу', null=True, blank=True)
    is_active = models.BooleanField('Показувати на сайті', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Гра'
        verbose_name_plural = 'Ігри'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('catalog:product_detail', args=[self.slug])

    def is_free(self):
        return self.price == 0

    def has_discount(self):
        return self.discount_price is not None and self.discount_price < self.price

    def final_price(self):
        if self.has_discount():
            return self.discount_price
        return self.price

    def discount_percent(self):
        if not self.has_discount():
            return 0
        return int(100 - self.discount_price / self.price * 100)


class ProductImage(models.Model):
    # скріншоти для сторінки гри
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Гра',
    )
    image = models.ImageField('Зображення', upload_to='screenshots/')
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Скріншот'
        verbose_name_plural = 'Скріншоти'
        ordering = ['order']

    def __str__(self):
        return f'Скріншот {self.product.title}'
