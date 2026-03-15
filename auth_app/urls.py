from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("", views.tasks, name="home"),              # 让根路径直接去任务页（可选）
    path("dashboard/", views.tasks, name="dashboard"),  # dashboard 也指向 tasks（符合 wireframe 主入口）
    path("tasks/", views.tasks, name="tasks"),
    path("sessions/", views.sessions, name="sessions"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("register/", views.register_view, name="register"),
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="auth_app/password_reset.html"
    ), name="password_reset"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="auth_app/password_reset_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="auth_app/password_reset_confirm.html"
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="auth_app/password_reset_complete.html"
    ), name="password_reset_complete")
]