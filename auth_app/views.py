from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from booking_app.models import Task, Session
from django.utils.timezone import now

def login_view(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get("next")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            if next_url:
                return redirect(next_url)

            if user.is_staff:
                return redirect("admin_dashboard")

            return redirect("dashboard")

        else:
            error = "Invalid username or password."

    return render(request, "auth_app/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard(request):

    # homepage redirect
    return redirect("task_list")


@login_required(login_url="login")
def tasks(request):
    return render(request, "task_list")


@login_required(login_url="login")
def sessions(request):
    return render(request, "auth_app/sessions.html")


@staff_member_required(login_url="login")
def admin_dashboard(request):
    total_users = User.objects.count()
    total_tasks = Task.objects.count()
    active_tasks = Task.objects.filter(is_active=True).count()
    completed_tasks = Task.objects.filter(is_active=False).count()
    total_sessions = Session.objects.count()
    completed_sessions = Session.objects.filter(status="completed").count()
    pending_sessions = Session.objects.filter(status="pending").count()
    in_progress_sessions = Session.objects.filter(status="in_progress").count()
    cancelled_sessions = Session.objects.filter(status="cancelled").count()
    today = now().date()

    tasks_today = Task.objects.filter(created_at__date=today).count()
    sessions_today = Session.objects.filter(created_at__date=today).count()
    active_users = User.objects.filter(last_login__date=today).count()

    recent_users = User.objects.order_by("-date_joined")[:5]
    recent_tasks = Task.objects.select_related("user").order_by("-created_at")[:5]
    recent_sessions = Session.objects.select_related("user", "task").order_by("-created_at")[:5]
    top_users = User.objects.order_by("-last_login")[:5]

    return render(
        request,
        "auth_app/admin_dashboard.html",
        {
            "total_users": total_users,
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "pending_sessions": pending_sessions,
            "in_progress_sessions": in_progress_sessions,
            "cancelled_sessions": cancelled_sessions,
            "tasks_today": tasks_today,
            "sessions_today": sessions_today,
            "active_users": active_users,
            "recent_users": recent_users,
            "recent_tasks": recent_tasks,
            "recent_sessions": recent_sessions,
            "top_users": top_users,
        },
    )

def register_view(request):

    if request.user.is_authenticated:
        return redirect("task_list")

    error = None

    if request.method == "POST":

        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "").strip()
        password2 = request.POST.get("password2", "").strip()

        if not email or not username or not password1 or not password2:
            error = "Please fill in all fields."

        elif password1 != password2:
            error = "Passwords do not match."

        else:
            try:
                User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1
                )

                return redirect("login")

            except IntegrityError:
                error = "Username already exists."

    return render(request, "auth_app/register.html", {"error": error})