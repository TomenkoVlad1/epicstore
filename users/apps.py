from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Користувачі'

    def ready(self):
        # підключаємо сигнали, інакше вони не спрацюють
        import users.signals  # noqa
