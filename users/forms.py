from datetime import date
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, UserProfile


class RegisterForm(UserCreationForm):
    # ці поля лежать в профілі, а не в юзері, тому додаю їх вручну
    country = forms.CharField(label='Країна', max_length=100, required=False)
    birth_date = forms.DateField(
        label='Дата народження',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email']

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > date.today():
            raise forms.ValidationError('Дата народження не може бути в майбутньому')
        return birth_date

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # профіль вже створив сигнал, просто заповнюємо його
            profile = user.profile
            profile.country = self.cleaned_data.get('country', '')
            profile.birth_date = self.cleaned_data.get('birth_date')
            profile.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'country', 'birth_date']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        # перевіряємо тільки новий файл (у старого вже нема content_type)
        if avatar and hasattr(avatar, 'content_type'):
            if avatar.size > settings.MAX_AVATAR_SIZE:
                raise forms.ValidationError('Аватар має бути не більше 2 МБ')
            if avatar.content_type not in ('image/jpeg', 'image/png', 'image/webp', 'image/gif'):
                raise forms.ValidationError('Можна завантажити тільки JPG, PNG, WEBP або GIF')
        return avatar

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > date.today():
            raise forms.ValidationError('Дата народження не може бути в майбутньому')
        return birth_date


class TopUpForm(forms.Form):
    amount = forms.DecimalField(
        label='Сума, USD',
        min_value=Decimal('0.01'),
        max_value=Decimal('10000'),
        decimal_places=2,
    )
