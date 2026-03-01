from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/tasks/'), name='home'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/book/', views.session_book, name='session_book'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/progress/', views.session_update_progress, name='session_progress'),
    path('sessions/<int:pk>/cancel/', views.session_cancel, name='session_cancel'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('sessions/<int:pk>/reschedule/', views.session_reschedule, name='session_reschedule'),
]