from django.contrib import admin

from .models import Subscribe, User

EMPTY_VALUE = '-пусто-'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Представляет модель User в интерфейсе администратора."""
    list_display = ('id', 'username', 'first_name',
                    'last_name', 'email', 'password')
    list_filter = ('email', 'username', )
    empty_value_display = EMPTY_VALUE


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    """Представляет модель Subscribe в интерфейсе администратора."""
    list_display = ('id', 'user', 'author')
    search_fields = ('user',)
    list_filter = ('user', )
    empty_value_display = EMPTY_VALUE
