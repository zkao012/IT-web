from django.urls import path
from . import views

urlpatterns = [

    # homepage
    path("", views.dashboard, name="dashboard"),

    # authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    # main pages
    path("tasks/", views.tasks, name="tasks"),
    path("sessions/", views.sessions, name="sessions"),

    # admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]