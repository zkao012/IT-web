from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db import IntegrityError

def login_view(request):
    # 已登录用户直接去 dashboard
    if request.user.is_authenticated:
        next_url = request.GET.get("next") or "tasks"
        return redirect(next_url)

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)  # 写入 session
            next_url = request.GET.get("next") or request.POST.get("next") or "tasks"
            return redirect(next_url)
        error = "用户名或密码错误"

    return render(request, "auth_app/login.html", {"error": error})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required(login_url="login")
def dashboard(request):
    return render(request, "auth_app/dashboard.html")

@login_required(login_url="login")
def tasks(request):
    return render(request, "auth_app/tasks.html")


@login_required(login_url="login")
def sessions(request):
    return render(request, "auth_app/sessions.html")


@staff_member_required(login_url="login")
def admin_dashboard(request):
    return render(request, "auth_app/admin_dashboard.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect("tasks")

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password1 = request.POST.get("password1", "").strip()
        password2 = request.POST.get("password2", "").strip()

        if not email or not username or not password1 or not password2:
            error = "请填写所有字段"
        elif password1 != password2:
            error = "两次密码不一致"
        else:
            try:
                User.objects.create_user(username=username, email=email, password=password1)
                return redirect("login")
            except IntegrityError:
                error = "用户名已存在，请换一个"

    return render(request, "auth_app/register.html", {"error": error})
