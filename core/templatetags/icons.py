"""
Чорно-білі лінійні іконки замість емодзі.
Використання в шаблоні:
    {% load icons %}
    {% icon 'cart' %}            - звичайна 20px
    {% icon 'heart' 16 %}        - свій розмір
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# всі іконки 24x24, малюються лінією кольору тексту (currentColor)
ICONS = {
    'store': '<path d="M6 7h12l1 13H5L6 7z"/><path d="M9 7V5a3 3 0 0 1 6 0v2"/>',
    'library': '<path d="M5 4v16M9 4v16"/><path d="M13 5l4-1 3 15-4 1z"/>',
    'cart': '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/>'
            '<path d="M2 3h3l2.5 12h12L22 7H6.2"/>',
    'wallet': '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M16 15h2"/>',
    'users': '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
             '<path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14c2.2.6 3.5 2.8 3.5 6"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    'user-plus': '<circle cx="10" cy="8" r="3.5"/><path d="M3.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
                 '<path d="M19 8v6M16 11h6"/>',
    'chat': '<path d="M4 5h16v11H9l-5 4z"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'plus-circle': '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    'x': '<path d="M6 6l12 12M18 6L6 18"/>',
    'check': '<path d="M5 12.5l4.5 4.5L19 7"/>',
    'check-circle': '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
    'alert': '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>',
    'heart': '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    'heart-fill': '<path fill="currentColor" d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    'search': '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    'logout': '<path d="M14 4h5v16h-5M10 8l-4 4 4 4M6 12h10"/>',
    'send': '<path d="M4 12l16-8-6 16-2.5-6.5z"/>',
    'tag': '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
    'gift': '<rect x="3" y="8" width="18" height="4"/><path d="M5 12v9h14v-9M12 8v13"/>'
            '<path d="M12 8S11 3 7.5 3 6 8 12 8zM12 8s1-5 4.5-5S18 8 12 8z"/>',
    'sparkle': '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
    'news': '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',
    'trash': '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    'more': '<circle cx="5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>'
            '<circle cx="19" cy="12" r="1.2" fill="currentColor"/>',
    'play': '<path fill="currentColor" d="M7 5l12 7-12 7z"/>',
    'arrow-right': '<path d="M5 12h14M13 6l6 6-6 6"/>',
    'image': '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 8"/>',
}


@register.simple_tag
def icon(name, size=20, css_class=''):
    paths = ICONS.get(name, '')
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">{}</svg>',
        css_class, size, size, mark_safe(paths),
    )
