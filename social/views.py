from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Friendship, Message, ChatGroup, GroupMessage, GroupInvite
from core.ratelimit import ratelimit
from .utils import get_friends, are_friends, friends_with_unread

User = get_user_model()


# ---------------- друзі ----------------

@login_required
@require_POST
@ratelimit('friend_add', limit=20, period=60)
def friend_add(request):
    username = request.POST.get('username', '').strip()
    other = User.objects.filter(username__iexact=username).first()

    if not other:
        messages.error(request, f'Користувача «{username}» не знайдено')
    elif other == request.user:
        messages.error(request, 'Не можна додати в друзі самого себе 🙂')
    elif are_friends(request.user, other):
        messages.error(request, f'{other.username} вже у вас в друзях')
    else:
        # якщо він вже кидав нам заявку - просто приймаємо її
        reverse_request = Friendship.objects.filter(from_user=other, to_user=request.user).first()
        if reverse_request:
            reverse_request.accepted = True
            reverse_request.save()
            messages.success(request, f'Тепер ви з {other.username} друзі!')
        else:
            Friendship.objects.get_or_create(from_user=request.user, to_user=other)
            messages.success(request, f'Заявку надіслано {other.username}')

    return redirect('users:profile')


@login_required
@require_POST
def friend_accept(request, pk):
    friendship = get_object_or_404(Friendship, pk=pk, to_user=request.user)
    friendship.accepted = True
    friendship.save()
    messages.success(request, f'Тепер ви з {friendship.from_user.username} друзі!')
    return redirect('users:profile')


@login_required
@require_POST
def friend_decline(request, pk):
    # відхилити вхідну або скасувати свою заявку
    friendship = get_object_or_404(
        Friendship, Q(to_user=request.user) | Q(from_user=request.user), pk=pk, accepted=False
    )
    friendship.delete()
    messages.info(request, 'Заявку видалено')
    return redirect('users:profile')


@login_required
@require_POST
def friend_remove(request, username):
    other = get_object_or_404(User, username=username)
    Friendship.objects.filter(
        Q(from_user=request.user, to_user=other) | Q(from_user=other, to_user=request.user)
    ).delete()
    messages.success(request, f'{other.username} видалено з друзів')
    return redirect('users:profile')


# ---------------- чати ----------------

def chat_sidebar(user):
    """Список зліва: групи + друзі з кількістю непрочитаних."""
    friends_list = friends_with_unread(user)
    # у кого є непрочитані - вище
    friends_list.sort(key=lambda x: -x['unread'])
    return {
        # кількість учасників рахуємо в тому ж запиті, а не окремо для кожної групи
        'chat_groups': user.chat_groups.annotate(member_count=Count('members')),
        'chat_friends': friends_list,
    }


@login_required
def chats(request):
    return render(request, 'social/chats.html', chat_sidebar(request.user))


@login_required
@ratelimit('send_message', limit=30, period=60)
def dm(request, username):
    other = get_object_or_404(User.objects.select_related('profile'), username=username)
    if not are_friends(request.user, other):
        messages.error(request, 'Писати можна тільки друзям')
        return redirect('social:chats')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(sender=request.user, recipient=other, text=text)
        return redirect('social:dm', username=other.username)

    # позначаємо його повідомлення як прочитані
    Message.objects.filter(sender=other, recipient=request.user, is_read=False).update(is_read=True)

    msgs = Message.objects.filter(
        Q(sender=request.user, recipient=other) | Q(sender=other, recipient=request.user)
    ).select_related('sender')
    invites = GroupInvite.objects.filter(
        Q(from_user=request.user, to_user=other) | Q(from_user=other, to_user=request.user)
    ).select_related('group', 'from_user', 'to_user')

    # змішуємо повідомлення і запрошення в одну стрічку по часу
    timeline = [{'type': 'msg', 'obj': m, 'time': m.created_at} for m in msgs]
    timeline += [{'type': 'invite', 'obj': i, 'time': i.created_at} for i in invites]
    timeline.sort(key=lambda x: x['time'])

    context = chat_sidebar(request.user)
    context.update({'other': other, 'timeline': timeline})
    return render(request, 'social/dm.html', context)


# ---------------- групи ----------------

@login_required
@ratelimit('group_create', limit=10, period=60)
def group_create(request):
    friends = get_friends(request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Введіть назву групи')
        else:
            group = ChatGroup.objects.create(name=name, owner=request.user)
            group.members.add(request.user)

            # друзям летять запрошення в лс, а не одразу в групу
            invited_ids = request.POST.getlist('friends')
            for friend in friends.filter(id__in=invited_ids):
                GroupInvite.objects.create(group=group, from_user=request.user, to_user=friend)

            messages.success(request, f'Групу «{name}» створено, запрошення надіслано')
            return redirect('social:group_detail', pk=group.pk)

    context = chat_sidebar(request.user)
    context['friends'] = friends
    return render(request, 'social/group_create.html', context)


@login_required
@ratelimit('send_message', limit=30, period=60)
def group_detail(request, pk):
    group = get_object_or_404(ChatGroup, pk=pk, members=request.user)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            GroupMessage.objects.create(group=group, sender=request.user, text=text)
        return redirect('social:group_detail', pk=group.pk)

    # кого ще можна запросити: друзі, яких нема в групі і яким ще не надіслали запрошення
    pending_ids = group.invites.filter(status=GroupInvite.PENDING).values_list('to_user_id', flat=True)
    can_invite = get_friends(request.user).exclude(chat_groups=group).exclude(id__in=pending_ids)

    context = chat_sidebar(request.user)
    context.update({
        'group': group,
        'group_messages': group.messages.select_related('sender', 'sender__profile'),
        'members': group.members.select_related('profile'),
        'can_invite': can_invite,
    })
    return render(request, 'social/group_detail.html', context)


@login_required
@require_POST
def group_invite(request, pk):
    group = get_object_or_404(ChatGroup, pk=pk, members=request.user)
    friends = get_friends(request.user).exclude(chat_groups=group)
    for friend in friends.filter(id__in=request.POST.getlist('friends')):
        GroupInvite.objects.get_or_create(
            group=group, to_user=friend, status=GroupInvite.PENDING,
            defaults={'from_user': request.user},
        )
    messages.success(request, 'Запрошення надіслано')
    return redirect('social:group_detail', pk=group.pk)


@login_required
@require_POST
def group_leave(request, pk):
    group = get_object_or_404(ChatGroup, pk=pk, members=request.user)
    group.members.remove(request.user)
    # якщо нікого не лишилось - видаляємо групу
    if not group.members.exists():
        group.delete()
    messages.success(request, 'Ви вийшли з групи')
    return redirect('social:chats')


@login_required
@require_POST
def invite_respond(request, pk):
    invite = get_object_or_404(GroupInvite, pk=pk, to_user=request.user, status=GroupInvite.PENDING)

    if request.POST.get('answer') == 'yes':
        invite.status = GroupInvite.ACCEPTED
        invite.save()
        invite.group.members.add(request.user)
        messages.success(request, f'Ви приєднались до групи «{invite.group.name}»')
        return redirect('social:group_detail', pk=invite.group.pk)

    invite.status = GroupInvite.DECLINED
    invite.save()
    messages.info(request, f'Ви відхилили запрошення в «{invite.group.name}»')
    return redirect('social:dm', username=invite.from_user.username)
