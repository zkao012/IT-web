from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Root → dashboard
    path('', RedirectView.as_view(url='/dashboard/'), name='home'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    path('manage/users/<int:pk>/', views.admin_user_detail, name='admin_user_detail'),
    path('manage/users/<int:pk>/toggle/', views.admin_user_toggle, name='admin_user_toggle'),
    path('manage/categories/', views.admin_category_list, name='admin_category_list'),
    path('manage/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('manage/categories/<int:pk>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('manage/categories/<int:pk>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('manage/tasks/', views.admin_task_list, name='admin_task_list'),
    path('manage/sessions/', views.admin_session_list, name='admin_session_list'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Progress / Statistics
    path('progress/', views.progress_list, name='progress_list'),
    path('statistics/', views.statistics, name='statistics'),

    # Tasks
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    # Sessions
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/book/', views.session_book, name='session_book'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/progress/', views.session_update_progress, name='session_progress'),
    path('sessions/<int:pk>/cancel/', views.session_cancel, name='session_cancel'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('sessions/<int:pk>/reschedule/', views.session_reschedule, name='session_reschedule'),
]
