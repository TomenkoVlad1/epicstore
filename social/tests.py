from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser
from .models import Friendship, ChatGroup, GroupInvite
from .utils import are_friends


def make_user(name):
    return CustomUser.objects.create_user(name, f'{name}@test.com', 'StrongPass123!')


class FriendsTests(TestCase):
    def setUp(self):
        self.vlad = make_user('vlad')
        self.timmy = make_user('timmy')

    def test_request_and_accept(self):
        self.client.force_login(self.vlad)
        self.client.post(reverse('social:friend_add'), {'username': 'timmy'})
        request = Friendship.objects.get(from_user=self.vlad, to_user=self.timmy)
        self.assertFalse(are_friends(self.vlad, self.timmy))

        self.client.force_login(self.timmy)
        self.client.post(reverse('social:friend_accept', args=[request.id]))
        self.assertTrue(are_friends(self.vlad, self.timmy))

    def test_cannot_add_yourself(self):
        self.client.force_login(self.vlad)
        self.client.post(reverse('social:friend_add'), {'username': 'vlad'})
        self.assertFalse(Friendship.objects.exists())

    def test_cannot_message_stranger(self):
        self.client.force_login(self.vlad)
        response = self.client.get(reverse('social:dm', args=['timmy']))
        self.assertRedirects(response, reverse('social:chats'))


class GroupInviteTests(TestCase):
    def setUp(self):
        self.owner = make_user('owner')
        self.friend = make_user('friend')
        Friendship.objects.create(from_user=self.owner, to_user=self.friend, accepted=True)

    def test_friend_joins_only_after_accepting(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('social:group_create'), {'name': 'Squad', 'friends': [self.friend.id]})
        group = ChatGroup.objects.get(name='Squad')
        invite = GroupInvite.objects.get(group=group, to_user=self.friend)
        # поки не прийняв - не в групі
        self.assertNotIn(self.friend, group.members.all())

        self.client.force_login(self.friend)
        self.client.post(reverse('social:invite_respond', args=[invite.id]), {'answer': 'yes'})
        self.assertIn(self.friend, group.members.all())

    def test_outsider_cannot_open_group(self):
        group = ChatGroup.objects.create(name='Secret', owner=self.owner)
        group.members.add(self.owner)
        self.client.force_login(self.friend)
        response = self.client.get(reverse('social:group_detail', args=[group.id]))
        self.assertEqual(response.status_code, 404)
