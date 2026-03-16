from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
import json

from .models import Session, Task, Category
from .forms import SessionBookForm, ProgressUpdateForm, TaskForm


# ========== Task Views ==========

@login_required
def task_list(request):
    active_tasks = Task.objects.filter(user=request.user, is_active=True)
    in_progress = [t for t in active_tasks if t.progress_percent() < 100]
    completed = [t for t in active_tasks if t.progress_percent() >= 100]

    paginator = Paginator(in_progress, 8)
    page = request.GET.get('page', 1)
    in_progress_page = paginator.get_page(page)

    # 用范围查询避免 MySQL __date 过滤问题
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # 全局连续学习 streak（最多往前查30天）
    streak = 0
    for i in range(30):
        day_start = today_start - timezone.timedelta(days=i)
        day_end = today_end - timezone.timedelta(days=i)
        has_session = Session.objects.filter(
            user=request.user,
            planned_start__gte=day_start,
            planned_start__lte=day_end,
        ).exclude(status__in=['cancelled', 'pending']).exists()
        if has_session:
            streak += 1
        else:
            break

    # 本周已学时长
    week_start = today_start - timezone.timedelta(days=today_start.weekday())
    week_minutes = Session.objects.filter(
        user=request.user,
        planned_start__gte=week_start,
        planned_start__lte=today_end,
    ).exclude(status__in=['cancelled', 'pending']).aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0

    # 今日已学时长
    today_minutes = Session.objects.filter(
        user=request.user,
        planned_start__gte=today_start,
        planned_start__lte=today_end,
    ).exclude(status__in=['cancelled', 'pending']).aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0

    return render(request, 'sessions/task_list.html', {
        'in_progress': in_progress_page,
        'completed': completed,
        'streak': streak,
        'week_minutes': week_minutes,
        'today_minutes': today_minutes,
    })


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, 'Task created successfully!')
            return redirect('task_list')
    else:
        form = TaskForm()
    return render(request, 'sessions/task_form.html', {'form': form})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    # 删除 task 时所有关联 session 一起删
    task.sessions.all().delete()
    task.is_active = False
    task.save()
    messages.success(request, 'Task deleted.')
    return redirect('task_list')


# ========== Session Views ==========

@login_required
def session_list(request):
    status_filter = request.GET.get('status', '')
    now = timezone.now()

    Session.objects.filter(
        user=request.user,
        status='pending',
        planned_start__lte=now
    ).update(status='in_progress')

    sessions = Session.objects.filter(user=request.user)
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    return render(request, 'sessions/session_list.html', {
        'sessions': sessions,
        'status_filter': status_filter,
    })


@login_required
def session_book(request):
    tasks_remaining = {}
    for task in request.user.tasks.filter(is_active=True):
        remaining = task.target_minutes - task.total_actual_minutes()
        tasks_remaining[task.pk] = max(remaining, 0)

    if request.method == 'POST':
        form = SessionBookForm(request.POST, user=request.user)
        if form.is_valid():
            if hasattr(form, 'overtime_warning'):
                messages.warning(request, form.overtime_warning)
            session = form.save(commit=False)
            session.user = request.user
            session.save()
            messages.success(request, 'Session booked successfully!')
            return redirect('session_list')
    else:
        task_id = request.GET.get('task_id')
        initial = {'task': task_id} if task_id else {}
        form = SessionBookForm(user=request.user, initial=initial)

    return render(request, 'sessions/session_book.html', {
        'form': form,
        'tasks_remaining': tasks_remaining,
    })


@login_required
def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk, user=request.user)

    now = timezone.now()
    if session.status == 'pending' and session.planned_start <= now:
        session.status = 'in_progress'
        session.save()

    progress_form = ProgressUpdateForm(instance=session)
    return render(request, 'sessions/session_detail.html', {
        'session': session,
        'progress_form': progress_form,
    })


@login_required
@require_POST
def session_update_progress(request, pk):
    session = get_object_or_404(Session, pk=pk, user=request.user)

    if session.status == 'cancelled':
        return JsonResponse({'error': 'Cannot update a cancelled session.'}, status=400)

    if session.status == 'pending':
        return JsonResponse({'error': 'This session has not started yet. Adjust the time if you want to log progress early.'}, status=400)

    try:
        data = json.loads(request.body)
        actual_minutes = int(data.get('actual_minutes', session.actual_minutes))
        completion_percent = int(data.get('completion_percent', session.completion_percent))
        notes = data.get('notes', session.notes)
        mark_complete = data.get('mark_complete', False)

        if actual_minutes == 0:
            return JsonResponse({'error': 'Please enter actual time spent before saving progress.'}, status=400)
        if actual_minutes < 0:
            return JsonResponse({'error': 'actual_minutes cannot be negative.'}, status=400)

        # 实际时长上限：计划时长的3倍
        max_minutes = session.planned_minutes() * 3
        if actual_minutes > max_minutes:
            return JsonResponse({'error': f'Time seems too high. Max allowed: {max_minutes} min (3x planned).'}, status=400)

        if not (0 <= completion_percent <= 100):
            return JsonResponse({'error': 'completion_percent must be between 0 and 100.'}, status=400)

        session.actual_minutes = actual_minutes
        session.completion_percent = completion_percent
        session.notes = notes

        # 普通保存 → in_progress，点 Mark as Complete → completed
        if mark_complete:
            session.status = 'completed'
        else:
            session.status = 'in_progress'

        session.save()

        return JsonResponse({
            'success': True,
            'status': session.status,
            'status_display': session.get_status_display(),
            'actual_minutes': session.actual_minutes,
            'completion_percent': session.completion_percent,
        })

    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)


@login_required
@require_POST
def session_cancel(request, pk):
    session = get_object_or_404(Session, pk=pk, user=request.user)

    if session.status in ['completed', 'cancelled']:
        messages.error(request, 'This session cannot be cancelled.')
    else:
        session.status = 'cancelled'
        session.save()
        messages.success(request, 'Session cancelled.')

    return redirect('session_list')


@login_required
@require_POST
def session_delete(request, pk):
    session = get_object_or_404(Session, pk=pk, user=request.user)
    if session.status == 'cancelled':
        session.delete()
        messages.success(request, 'Session deleted.')
    return redirect('session_list')


@login_required
@require_POST
def session_reschedule(request, pk):
    session = get_object_or_404(Session, pk=pk, user=request.user)

    if session.status not in ['pending', 'in_progress']:
        return JsonResponse({'error': 'Cannot reschedule this session.'}, status=400)

    try:
        data = json.loads(request.body)
        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import make_aware, is_naive

        new_start = parse_datetime(data.get('planned_start'))
        new_end = parse_datetime(data.get('planned_end'))

        if not new_start or not new_end:
            return JsonResponse({'error': 'Invalid date format.'}, status=400)
        if new_end <= new_start:
            return JsonResponse({'error': 'End time must be after start time.'}, status=400)

        if is_naive(new_start):
            new_start = make_aware(new_start)
        if is_naive(new_end):
            new_end = make_aware(new_end)

        # 冲突检测
        conflicts = Session.objects.filter(
            user=request.user,
            planned_start__lt=new_end,
            planned_end__gt=new_start,
        ).exclude(status='cancelled').exclude(pk=pk)
        if conflicts.exists():
            return JsonResponse({'error': 'This time slot conflicts with another session.'}, status=400)

        session.planned_start = new_start
        session.planned_end = new_end

        now = timezone.now()
        if session.status == 'pending' and new_start <= now:
            session.status = 'in_progress'

        session.save()
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)