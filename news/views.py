from django.shortcuts import render, get_object_or_404

from .models import News


def news_list(request):
    news = News.objects.filter(is_published=True).select_related('product')
    return render(request, 'news/news_list.html', {'news_list': news})


def news_detail(request, slug):
    item = get_object_or_404(News.objects.select_related('product'), slug=slug, is_published=True)
    # ще кілька новин знизу
    other = News.objects.filter(is_published=True).exclude(id=item.id)[:3]
    return render(request, 'news/news_detail.html', {'item': item, 'other_news': other})
