from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Progress
from .forms import ProgressForm


@login_required
def progress_list(request):
    pending = Progress.objects.filter(user=request.user, completed=False).order_by("-created_at")
    done = Progress.objects.filter(user=request.user, completed=True).order_by("-created_at")
    return render(request, "progress_app/progress_list.html", {"pending": pending, "done": done})


@login_required
def progress_add(request):
    if request.method == "POST":
        form = ProgressForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("progress_app:list")
    else:
        form = ProgressForm()
    return render(request, "progress_app/progress_form.html", {"form": form, "mode": "add"})


@login_required
def progress_edit(request, pk):
    obj = get_object_or_404(Progress, pk=pk, user=request.user)
    if request.method == "POST":
        form = ProgressForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("progress_app:list")
    else:
        form = ProgressForm(instance=obj)
    return render(request, "progress_app/progress_form.html", {"form": form, "mode": "edit"})


@login_required
def progress_delete(request, pk):
    obj = get_object_or_404(Progress, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        return redirect("progress_app:list")
    return render(request, "progress_app/progress_confirm_delete.html", {"item": obj})


@login_required
@require_POST
def mark_done(request, pk):
    obj = get_object_or_404(Progress, pk=pk, user=request.user)
    obj.completed = True
    obj.completion_percent = 100
    obj.save(update_fields=["completed", "completion_percent"])
    return redirect("progress_app:list")