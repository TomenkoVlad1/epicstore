from django.db import models
from django.urls import reverse

from catalog.models import Product


class News(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField(unique=True)
    image = models.ImageField('Картинка', upload_to='news/', blank=True)
    short_text = models.CharField('Короткий опис', max_length=300, blank=True)
    text = models.TextField('Текст')
    # новина може бути про якусь гру
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='news', verbose_name='Гра',
    )
    is_published = models.BooleanField('Опубліковано', default=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Новина'
        verbose_name_plural = 'Новини'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news:news_detail', args=[self.slug])
