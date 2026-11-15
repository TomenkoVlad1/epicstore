from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Friendship(models.Model):
    """Заявка в друзі. Коли друг прийняв - accepted = True."""
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friendships')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friendships')
    accepted = models.BooleanField('Прийнято', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Дружба / заявка'
        verbose_name_plural = 'Друзі та заявки'
        unique_together = ['from_user', 'to_user']

    def __str__(self):
        status = 'друзі' if self.accepted else 'заявка'
        return f'{self.from_user} → {self.to_user} ({status})'


class Message(models.Model):
    """Особисте повідомлення (лс)."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField('Текст')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Повідомлення'
        verbose_name_plural = 'Повідомлення'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} → {self.recipient}: {self.text[:30]}'


class ChatGroup(models.Model):
    name = models.CharField('Назва групи', max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_groups')
    members = models.ManyToManyField(User, related_name='chat_groups', verbose_name='Учасники')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Група'
        verbose_name_plural = 'Групи'

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField('Текст')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.group}: {self.text[:30]}'


class GroupInvite(models.Model):
    """Запрошення в групу - показується в лс між тим хто запросив і тим кого запросили."""
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    STATUS_CHOICES = [
        (PENDING, 'Очікує'),
        (ACCEPTED, 'Прийнято'),
        (DECLINED, 'Відхилено'),
    ]

    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name='invites')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_invites')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_invites')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Запрошення в групу'
        verbose_name_plural = 'Запрошення в групи'

    def __str__(self):
        return f'{self.from_user} запросив {self.to_user} в {self.group}'
