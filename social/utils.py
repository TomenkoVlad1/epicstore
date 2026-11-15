from collections import Counter

from django.contrib.auth import get_user_model
from django.db.models import Q, Count

from .models import Friendship, Message, GroupInvite

User = get_user_model()


def get_friends(user):
    """Всі друзі юзера (заявка могла бути з будь-якого боку). 2 запити, незалежно від кількості друзів."""
    pairs = (
        Friendship.objects.filter(accepted=True)
        .filter(Q(from_user=user) | Q(to_user=user))
        .values_list('from_user_id', 'to_user_id')
    )
    friend_ids = {b if a == user.id else a for a, b in pairs}
    return User.objects.filter(id__in=friend_ids).select_related('profile').order_by('username')


def are_friends(user1, user2):
    return Friendship.objects.filter(accepted=True).filter(
        Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1)
    ).exists()


def unread_counts(user):
    """
    {id_друга: кількість непрочитаних повідомлень + запрошень}.
    Раніше рахувалось окремо для кожного друга (N+1), тепер 2 запити з GROUP BY.
    """
    counts = Counter()
    messages = (
        Message.objects.filter(recipient=user, is_read=False)
        .values('sender_id').annotate(c=Count('id'))
    )
    for row in messages:
        counts[row['sender_id']] += row['c']

    invites = (
        GroupInvite.objects.filter(to_user=user, status=GroupInvite.PENDING)
        .values('from_user_id').annotate(c=Count('id'))
    )
    for row in invites:
        counts[row['from_user_id']] += row['c']
    return counts


def friends_with_unread(user):
    counts = unread_counts(user)
    return [{'user': f, 'unread': counts.get(f.id, 0)} for f in get_friends(user)]


def unread_total(user):
    return sum(unread_counts(user).values())
