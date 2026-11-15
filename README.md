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
python manage.py runserver
```

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
```

Сайт: http://localhost:8000

## Що є

- Каталог: Цікавинки, Всеогляд (пошук через Q, фільтри, сортування), Новини
- Користувачі: реєстрація з країною і датою народження, профіль, баланс
- Кошик у сесії, оформлення з балансу, бібліотека з улюбленими і колекціями
- Друзі, особисті повідомлення, групи із запрошеннями
- Redis-кеш каталогу з інвалідацією через сигнали
- Rate limiting, production-налаштування через змінні середовища
