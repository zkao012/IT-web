from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from booking_app.models import Task
from .forms import ProgressTaskForm


@login_required
def progress_list(request):
    tasks = Task.objects.filter(user=request.user).order_by("-created_at")

    pending = [
        task for task in tasks
        if task.is_active and not task.is_completed()
    ]

    done = [
        task for task in tasks
        if (not task.is_active) or task.is_completed()
    ]

    return render(
        request,
        "progress_app/progress_list.html",
        {
            "pending": pending,
            "done": done,
        },
    )


@login_required
def progress_add(request):
    if request.method == "POST":
        form = ProgressTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.target_minutes = 60
            task.save()
            return redirect("progress_app:list")
    else:
        form = ProgressTaskForm()

    return render(
        request,
        "progress_app/progress_form.html",
        {
            "form": form,
            "mode": "add",
        },
    )


@login_required
def progress_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == "POST":
        form = ProgressTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect("progress_app:list")
    else:
        form = ProgressTaskForm(instance=task)

    return render(
        request,
        "progress_app/progress_form.html",
        {
            "form": form,
            "mode": "edit",
        },
    )


@login_required
def progress_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == "POST":
        task.sessions.all().delete()
        task.delete()
        return redirect("progress_app:list")

    return render(
        request,
        "progress_app/progress_confirm_delete.html",
        {"item": task},
    )


@login_required
@require_POST
def mark_done(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.is_active = False
    task.save(update_fields=["is_active"])
    return redirect("progress_app:list")