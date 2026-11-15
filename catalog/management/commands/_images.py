"""
Генерує картинки-заглушки (обкладинка, банер, скріншоти, картинка новини) через Pillow.
Файл починається з _ тому Django не вважає його командою.
"""
import hashlib
import math
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# шрифти: спочатку Windows (Arial), потім Linux (DejaVu, для докера)
FONT_CANDIDATES = {
    'bold': ['arialbd.ttf', 'C:/Windows/Fonts/arialbd.ttf', 'DejaVuSans-Bold.ttf',
             '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'],
    'regular': ['arial.ttf', 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
}


def get_font(size, weight='bold'):
    for path in FONT_CANDIDATES[weight]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def colors_for(text):
    """Для кожної назви - свої кольори, але завжди однакові (щоб при перезапуску не мінялись)."""
    seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
    rnd = random.Random(seed)
    palettes = [
        ((20, 24, 48), (88, 60, 180)), ((10, 30, 40), (20, 140, 160)),
        ((40, 10, 20), (190, 50, 70)), ((15, 15, 15), (90, 90, 100)),
        ((30, 20, 5), (200, 120, 30)), ((5, 30, 20), (40, 160, 100)),
        ((25, 5, 40), (170, 60, 200)), ((5, 20, 45), (40, 110, 220)),
    ]
    return palettes[seed % len(palettes)], rnd


def gradient(width, height, top, bottom, rnd):
    img = Image.new('RGB', (width, height), top)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)

    # кілька розмитих "плям" світла, щоб не було пласко
    glow = Image.new('RGB', (width, height), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for _ in range(4):
        r = rnd.randint(min(width, height) // 6, min(width, height) // 2)
        x, y = rnd.randint(0, width), rnd.randint(0, height)
        c = tuple(min(255, int(bottom[i] * 1.4)) for i in range(3))
        gdraw.ellipse([x - r, y - r, x + r, y + r], fill=c)
    glow = glow.filter(ImageFilter.GaussianBlur(min(width, height) // 6))
    img = Image.blend(img, Image.composite(glow, img, glow.convert('L')), 0.55)

    # тонкі діагональні лінії - "сучасний" вигляд
    draw = ImageDraw.Draw(img)
    for i in range(-height, width, 60):
        draw.line([(i, height), (i + height, 0)], fill=tuple(min(255, c + 12) for c in top), width=1)
    return img


def wrap(draw, text, font, max_width):
    words, lines, line = text.split(), [], ''
    for word in words:
        test = f'{line} {word}'.strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit_text(draw, text, max_width, max_lines, start_size, min_size=18):
    size = start_size
    while size > min_size:
        font = get_font(size)
        lines = wrap(draw, text, font, max_width)
        if len(lines) <= max_lines and all(draw.textlength(l, font=font) <= max_width for l in lines):
            return font, lines
        size -= 4
    font = get_font(min_size)
    return font, wrap(draw, text, font, max_width)[:max_lines]


def to_bytes(img, quality=85):
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=quality, optimize=True)
    return buf.getvalue()


def make_cover(title, label):
    """Вертикальна обкладинка 600x800."""
    w, h = 600, 800
    (top, bottom), rnd = colors_for(title)
    img = gradient(w, h, top, bottom, rnd)
    draw = ImageDraw.Draw(img)

    # затемнення знизу під текст
    shade = Image.new('L', (w, h), 0)
    ImageDraw.Draw(shade).rectangle([0, h // 2, w, h], fill=170)
    shade = shade.filter(ImageFilter.GaussianBlur(80))
    img = Image.composite(Image.new('RGB', (w, h), (0, 0, 0)), img, shade)
    draw = ImageDraw.Draw(img)

    font, lines = fit_text(draw, title.upper(), w - 80, 4, 72)
    line_h = font.size + 10
    y = h - 90 - line_h * len(lines)
    for line in lines:
        draw.text((40, y), line, font=font, fill=(255, 255, 255))
        y += line_h

    draw.text((40, h - 60), label.upper(), font=get_font(20, 'regular'), fill=(200, 200, 200))
    draw.rectangle([40, 40, 110, 64], outline=(255, 255, 255), width=2)
    draw.text((49, 43), 'EPIC', font=get_font(16), fill=(255, 255, 255))
    return to_bytes(img)


def make_banner(title, subtitle):
    """Широкий банер 1600x900 для головної."""
    w, h = 1600, 900
    (top, bottom), rnd = colors_for(title + 'banner')
    img = gradient(w, h, top, bottom, rnd)

    # великі прозорі кола справа - як "арт" гри
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for i in range(6):
        r = 120 + i * 70
        cx, cy = int(w * 0.72), int(h * 0.5)
        odraw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 40 - i * 5), width=3)
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    draw = ImageDraw.Draw(img)
    font, lines = fit_text(draw, title, 780, 3, 110)
    y = 330
    for line in lines:
        draw.text((90, y), line, font=font, fill=(255, 255, 255))
        y += font.size + 14
    draw.text((92, y + 20), subtitle, font=get_font(34, 'regular'), fill=(220, 220, 220))
    return to_bytes(img)


def make_screenshot(title, number):
    """Скріншот 1280x720 - абстрактна "сцена" з горизонтом і горами."""
    w, h = 1280, 720
    (top, bottom), rnd = colors_for(f'{title}-{number}')
    img = gradient(w, h, bottom, top, rnd)
    draw = ImageDraw.Draw(img)

    # гори на горизонті
    for layer in range(3):
        base = int(h * (0.55 + layer * 0.12))
        shade = tuple(max(0, int(c * (0.5 - layer * 0.12))) for c in top)
        points = [(0, h)]
        x = 0
        while x <= w:
            points.append((x, base - rnd.randint(20, 160 - layer * 40)))
            x += rnd.randint(80, 200)
        points += [(w, base), (w, h)]
        draw.polygon(points, fill=shade)

    # "сонце"
    sx, sy, sr = rnd.randint(200, w - 200), rnd.randint(80, 260), rnd.randint(40, 90)
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 240, 220))

    draw.text((30, h - 50), f'{title} — скріншот {number}', font=get_font(24, 'regular'), fill=(230, 230, 230))
    return to_bytes(img, quality=80)


def make_news_image(title):
    """Картинка новини 1280x720."""
    w, h = 1280, 720
    (top, bottom), rnd = colors_for('news' + title)
    img = gradient(w, h, top, bottom, rnd)
    draw = ImageDraw.Draw(img)
    draw.text((70, 70), 'НОВИНИ', font=get_font(28), fill=(255, 255, 255))
    draw.line([(70, 115), (190, 115)], fill=(255, 255, 255), width=3)
    font, lines = fit_text(draw, title, w - 140, 3, 76)
    y = h - 90 - (font.size + 12) * len(lines)
    for line in lines:
        draw.text((70, y), line, font=font, fill=(255, 255, 255))
        y += font.size + 12
    return to_bytes(img)


# ---------------- емблеми жанрів ----------------

def _emblem_shapes(draw, cx, cy, s, kind, fill):
    """Малює емблему жанру лініями. s - половина розміру емблеми."""
    w = max(2, int(s * 0.09))  # товщина лінії

    def p(x, y):
        # координати в долях від s, відносно центру
        return (cx + x * s, cy + y * s)

    if kind == 'action':  # блискавка
        draw.polygon([p(0.15, -1), p(-0.55, 0.12), p(-0.05, 0.12), p(-0.2, 1),
                      p(0.55, -0.18), p(0.05, -0.18), p(0.3, -1)], fill=fill)
    elif kind == 'adventure':  # компас
        draw.ellipse([p(-0.95, -0.95), p(0.95, 0.95)], outline=fill, width=w)
        draw.polygon([p(0, -0.75), p(0.2, 0), p(0, 0.75), p(-0.2, 0)], fill=fill)
        draw.ellipse([p(-0.08, -0.08), p(0.08, 0.08)], fill=0)  # дірка в масці
    elif kind == 'rpg':  # меч
        draw.polygon([p(0, -1), p(0.13, -0.8), p(0.13, 0.35), p(-0.13, 0.35), p(-0.13, -0.8)], fill=fill)
        draw.rounded_rectangle([p(-0.5, 0.35), p(0.5, 0.5)], radius=int(s * 0.05), fill=fill)
        draw.rectangle([p(-0.07, 0.5), p(0.07, 0.85)], fill=fill)
        draw.ellipse([p(-0.14, 0.82), p(0.14, 1.0)], fill=fill)
    elif kind == 'shooter':  # приціл
        draw.ellipse([p(-0.75, -0.75), p(0.75, 0.75)], outline=fill, width=w)
        for a, b in [((0, -1), (0, -0.3)), ((0, 0.3), (0, 1)), ((-1, 0), (-0.3, 0)), ((0.3, 0), (1, 0))]:
            draw.line([p(*a), p(*b)], fill=fill, width=w)
        draw.ellipse([p(-0.1, -0.1), p(0.1, 0.1)], fill=fill)
    elif kind == 'racing':  # фінішний прапор
        draw.line([p(-0.8, -0.9), p(-0.8, 1)], fill=fill, width=w)
        cell = 0.3
        for row in range(4):
            for col in range(5):
                if (row + col) % 2 == 0:
                    x, y = -0.8 + col * cell, -0.9 + row * cell
                    draw.rectangle([p(x, y), p(x + cell, y + cell)], fill=fill)
        draw.rectangle([p(-0.8, -0.9), p(0.7, 0.3)], outline=fill, width=max(1, w // 2))
    elif kind == 'indie':  # геймпад
        draw.rounded_rectangle([p(-1, -0.5), p(1, 0.55)], radius=int(s * 0.45), outline=fill, width=w)
        draw.rectangle([p(-0.62, -0.06), p(-0.22, 0.08)], fill=fill)
        draw.rectangle([p(-0.49, -0.2), p(-0.35, 0.22)], fill=fill)
        for bx, by in [(0.38, -0.12), (0.6, 0.1)]:
            draw.ellipse([p(bx - 0.1, by - 0.1), p(bx + 0.1, by + 0.1)], fill=fill)
    elif kind == 'battle-royale':  # корона
        draw.polygon([p(-0.9, 0.5), p(-0.9, -0.5), p(-0.45, 0), p(0, -0.75),
                      p(0.45, 0), p(0.9, -0.5), p(0.9, 0.5)], fill=fill)
        draw.rectangle([p(-0.9, 0.62), p(0.9, 0.8)], fill=fill)
        for x, y in [(-0.9, -0.5), (0, -0.75), (0.9, -0.5)]:
            draw.ellipse([p(x - 0.1, y - 0.1), p(x + 0.1, y + 0.1)], fill=fill)
    elif kind == 'simulator':  # шестерня
        for i in range(8):
            a = math.pi / 4 * i
            draw.line([p(math.cos(a) * 0.45, math.sin(a) * 0.45), p(math.cos(a) * 0.95, math.sin(a) * 0.95)],
                      fill=fill, width=int(s * 0.28))
        draw.ellipse([p(-0.72, -0.72), p(0.72, 0.72)], fill=fill)
        draw.ellipse([p(-0.28, -0.28), p(0.28, 0.28)], fill=0)  # дірка в масці
    elif kind == 'strategy':  # шахова тура
        draw.polygon([p(-0.6, -0.9), p(-0.36, -0.9), p(-0.36, -0.7), p(-0.12, -0.7), p(-0.12, -0.9),
                      p(0.12, -0.9), p(0.12, -0.7), p(0.36, -0.7), p(0.36, -0.9), p(0.6, -0.9),
                      p(0.6, -0.45), p(0.4, -0.35), p(0.4, 0.55), p(0.65, 0.7), p(0.65, 0.95),
                      p(-0.65, 0.95), p(-0.65, 0.7), p(-0.4, 0.55), p(-0.4, -0.35), p(-0.6, -0.45)], fill=fill)
    elif kind == 'horror':  # привид
        draw.pieslice([p(-0.7, -0.95), p(0.7, 0.45)], 180, 360, fill=fill)
        draw.polygon([p(-0.7, -0.26), p(0.7, -0.26), p(0.7, 0.95), p(0.35, 0.65),
                      p(0, 0.95), p(-0.35, 0.65), p(-0.7, 0.95)], fill=fill)
        for ex in (-0.28, 0.28):
            draw.ellipse([p(ex - 0.13, -0.38), p(ex + 0.13, -0.08)], fill=0)  # дірка в масці
    else:  # невідомий жанр - ромб
        draw.polygon([p(0, -0.9), p(0.7, 0), p(0, 0.9), p(-0.7, 0)], outline=fill, width=w)


def draw_emblem(img, cx, cy, size, kind):
    """
    Малює на img (RGB) емблему жанру kind (= slug категорії) з центром (cx, cy).
    Біла емблема з м'яким світінням навколо. Змінює img на місці.
    """
    s = size / 2
    # маска емблеми: білим по чорному (чорні деталі - "дірки")
    mask = Image.new('L', img.size, 0)
    _emblem_shapes(ImageDraw.Draw(mask), cx, cy, s, kind, 255)

    glow = mask.filter(ImageFilter.GaussianBlur(max(4, size // 12)))
    img.paste(Image.new('RGB', img.size, (255, 255, 255)), (0, 0), glow.point(lambda v: v * 0.6))
    img.paste(Image.new('RGB', img.size, (255, 255, 255)), (0, 0), mask)
    return img


def make_category_image(slug):
    """Квадратна картинка категорії 400x400: темний градієнт + емблема жанру."""
    w = h = 400
    (top, bottom), rnd = colors_for('category-' + slug)
    img = gradient(w, h, top, bottom, rnd)
    # затемнення по краях, щоб емблема "світилась" у центрі
    vignette = Image.new('L', (w, h), 0)
    ImageDraw.Draw(vignette).ellipse([-80, -80, w + 80, h + 80], fill=0, outline=160, width=120)
    vignette = vignette.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new('RGB', (w, h), (0, 0, 0)), img, vignette)
    draw_emblem(img, w // 2, h // 2, 190, slug)
    return to_bytes(img, quality=88)


# ---------------- збереження згенерованих файлів ----------------
# Згенеровані картинки (і обкладинки з RAWG) завжди лежать як <папка>/<slug>.jpg.
# Все, що має інше ім'я - завантажено вручну через адмінку, і його не чіпаємо.

def generated_name(field_file, filename):
    """Повне ім'я файлу, наприклад covers/fortnite.jpg."""
    return f'{field_file.field.upload_to}{filename}'


def is_generated(field_file, filename):
    """True, якщо поле порожнє або в ньому наш згенерований файл."""
    return not field_file or field_file.name == generated_name(field_file, filename)


def save_generated(field_file, filename, data):
    """
    Записує data у <upload_to>/<filename>, перезаписуючи старий файл з тим самим ім'ям.
    Звичайний field.save() додав би до імені випадковий суфікс (fortnite_Ab12Cd.jpg),
    і потім ми б не впізнали свій файл. Модель не зберігає - треба викликати save() самому.
    """
    from django.core.files.base import ContentFile
    from django.core.files.storage import FileSystemStorage, default_storage

    storage = FileSystemStorage(
        location=default_storage.location, base_url=default_storage.base_url, allow_overwrite=True,
    )
    field_file.name = storage.save(generated_name(field_file, filename), ContentFile(data))
