"""
Генерує картинки-заглушки (обкладинка, банер, скріншоти, картинка новини) через Pillow.
Файл починається з _ тому Django не вважає його командою.
"""
import hashlib
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
