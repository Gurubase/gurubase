from django.contrib import admin
from django.utils.html import format_html
from accounts.models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_admin', 'user_picture', 'email', 'name', 'auth_provider', 'is_email_confirmed', 'date_created']
    ordering = ['-date_created']
    list_filter = ['auth_provider', 'is_admin']
    search_fields = ['id', 'email', 'name']

    def user_picture(self, obj):
        if obj.picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.picture)
        return '-'
    user_picture.short_description = 'Picture'
