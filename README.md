# Epic Store (Django)

Інтернет-магазин ігор у стилі Epic Games Store.

## Локальний запуск

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # Windows (на Linux/Mac: cp)
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_games      # 46 ігор, 12 новин і картинки до них
python manage.py fetch_covers    # (необов'язково) справжні обкладинки, див. нижче
python manage.py runserver
```

## Справжні обкладинки з RAWG

`seed_games` малює картинки-заглушки. Справжні обкладинки, банери і скріншоти
можна завантажити з [RAWG](https://rawg.io):

1. Зареєструйся на https://rawg.io і отримай безкоштовний ключ на https://rawg.io/apidocs
   (кнопка "Get API Key").
2. Додай ключ у `.env` (у код і на github він не потрапляє):
   ```
   RAWG_API_KEY=твій_ключ
   ```
3. Запусти:
   ```
   python manage.py fetch_covers                # всі ігри
   python manage.py fetch_covers gta-5 hades    # тільки вибрані (за slug)
   python manage.py fetch_covers --dry-run      # тільки перевірити, що ігри знаходяться
   python manage.py fetch_covers --force        # перезаписати і картинки з адмінки
   ```

Команда перезаписує тільки згенеровані файли (`covers/<slug>.jpg`, `banners/<slug>.jpg`,
`screenshots/<slug>-<n>.jpg`). Картинки, завантажені вручну через адмінку, не чіпає без `--force`.
В кінці виводить, які ігри знайдено, а які ні. Якщо гра знаходиться не та -
додай підказку в `TITLE_HINTS` у `catalog/management/commands/fetch_covers.py`.

Увага: `seed_games --redraw` знову замінить обкладинки з RAWG заглушками,
після нього треба ще раз запустити `fetch_covers`.

Дані та зображення ігор надає RAWG, посилання на rawg.io є у футері сайту (вимога їхньої ліцензії).

## Тести

```
python manage.py test
```

## Docker (Gunicorn + WhiteNoise + Redis)

```
copy .env.example .env    # і задати свій DJANGO_SECRET_KEY
docker compose up --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_games
docker compose exec web python manage.py fetch_covers
```

Сайт: http://localhost:8000

## Що є

- Каталог: Цікавинки (з блоком "Обрати за жанром"), Всеогляд з чипами жанрів (пошук через Q, фільтри, сортування), Новини
- Користувачі: реєстрація з країною і датою народження, профіль, баланс
- Кошик у сесії, оформлення з балансу, бібліотека з улюбленими і колекціями
- Друзі, особисті повідомлення, групи із запрошеннями
- Redis-кеш каталогу з інвалідацією через сигнали
- Rate limiting, production-налаштування через змінні середовища
