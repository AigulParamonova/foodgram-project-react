from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя."""
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=254,
        unique=True
    )
    username = models.CharField(
        'Уникальный юзернейм',
        max_length=150,
        unique=True
    )
    first_name = models.CharField(
        'Имя',
        max_length=150
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=150
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    """Модель подписки."""
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='follower',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        related_name='following',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author', ),
                name='unique_subscribe'),
        )
