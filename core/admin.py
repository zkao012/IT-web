from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Category, Task, Session

admin.site.unregister(User)

admin.site.unregister(Group)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    # 只保留必要字段，去掉多余 tab
    fieldsets = (
        ('Account', {'fields': ('username', 'email', 'password')}),
        ('Status', {'fields': ('is_active', 'is_staff')}),
    )
    add_fieldsets = (
        ('Create User', {
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff'),
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj == request.user:
            return False
        return True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'task_count', 'created_at', 'delete_button')
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('created_at',)
    actions = None 

    def task_count(self, obj):
        return format_html('<b>{}</b>', obj.task_set.count())
    task_count.short_description = 'Tasks'

    def delete_button(self, obj):
        return format_html(
            '<a href="/admin/core/category/{}/delete/" '
            'style="background:#EF4444;color:#fff;padding:4px 12px;'
            'border-radius:6px;font-size:12px;font-weight:600;'
            'text-decoration:none;">Delete</a>', obj.pk
        )
    delete_button.short_description = ''


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('title', 'user__username')
    readonly_fields = ('user', 'title', 'description', 'category', 
                       'target_minutes', 'is_active', 'created_at')

    def has_add_permission(self, request):
        return False  # 管理员不能新建

    def has_delete_permission(self, request, obj=None):
        return False  # 管理员不能删除


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'planned_start', 'planned_end', 'status', 'completion_percent')
    list_filter = ('status', 'user')
    search_fields = ('task__title', 'user__username')
    readonly_fields = ('task', 'user', 'planned_start', 'planned_end',
                       'actual_minutes', 'completion_percent', 'status', 
                       'notes', 'created_at')

    def has_add_permission(self, request):
        return False  # 管理员不能新建

    def has_delete_permission(self, request, obj=None):
        return False  # 管理员不能删除