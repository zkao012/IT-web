from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db import models
from django.db.models import Sum
import json

from .models import Session, Task, Category
from .forms import SessionBookForm, ProgressUpdateForm, TaskForm


# ========== Auth Views ==========

def login_view(request):
    if request.user.is_authenticated:
        return redirect('task_list')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if next_url:
                return redirect(next_url)
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect('dashboard')
        else:
            error = 'Invalid username or password.'

    return render(request, 'auth/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('task_list')

    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not email or not username or not password1 or not password2:
            error = 'Please fill in all fields.'
        elif password1 != password2:
            error = 'Passwords do not match.'
        else:
            from django.core.validators import validate_email as _validate_email
            from django.core.exceptions import ValidationError as _ValidationError
            try:
                _validate_email(email)
            except _ValidationError:
                error = 'Please enter a valid email address.'
            if error is None and User.objects.filter(email=email).exists():
                error = 'Email already registered.'
            if error is None:
                try:
                    user = User.objects.create_user(username=username, email=email, password=password1)
                    from django.contrib.auth import login as auth_login
                    auth_login(request, user)
                    return redirect('dashboard')
                except IntegrityError:
                    error = 'Username already exists.'

    return render(request, 'auth/register.html', {'error': error})


# ========== Admin Dashboard ==========

@staff_member_required(login_url='login')
def admin_dashboard(request):
    today = timezone.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)

    return render(request, 'auth/admin_dashboard.html', {
        'total_users': User.objects.count(),
        'total_tasks': Task.objects.count(),
        'active_tasks': Task.objects.filter(is_active=True).count(),
        'completed_tasks': Task.objects.filter(is_active=False).count(),
        'total_sessions': Session.objects.count(),
        'completed_sessions': Session.objects.filter(status='completed').count(),
        'pending_sessions': Session.objects.filter(status='pending').count(),
        'in_progress_sessions': Session.objects.filter(status='in_progress').count(),
        'cancelled_sessions': Session.objects.filter(status='cancelled').count(),
        'tasks_today': Task.objects.filter(created_at__gte=today_start, created_at__lte=today_end).count(),
        'sessions_today': Session.objects.filter(created_at__gte=today_start, created_at__lte=today_end).count(),
        'active_users': User.objects.filter(last_login__gte=today_start, last_login__lte=today_end).count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_sessions': Session.objects.select_related('user', 'task').order_by('-created_at')[:5],
    })


# ========== Admin Views ===========

@staff_member_required(login_url='login')
def admin_dashboard(request):
    from django.db.models import Sum, Avg
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    week_start = today_start - timezone.timedelta(days=today_start.weekday())

    # Platform stats
    total_users = User.objects.filter(is_staff=False).count()
    active_users_today = User.objects.filter(
        is_staff=False, last_login__gte=today_start, last_login__lte=today_end
    ).count()
    new_users_today = User.objects.filter(
        is_staff=False, date_joined__gte=today_start
    ).count()
    disabled_users = User.objects.filter(is_staff=False, is_active=False).count()

    total_tasks = Task.objects.count()
    tasks_today = Task.objects.filter(created_at__gte=today_start).count()
    completed_tasks = Task.objects.filter(is_active=True).count()

    total_sessions = Session.objects.count()
    sessions_today = Session.objects.filter(created_at__gte=today_start).count()
    completed_sessions = Session.objects.filter(status='completed').count()
    pending_sessions = Session.objects.filter(status='pending').count()
    in_progress_sessions = Session.objects.filter(status='in_progress').count()
    cancelled_sessions = Session.objects.filter(status='cancelled').count()

    # Weekly activity - sessions per day
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        day_start = today_start - timezone.timedelta(days=i)
        day_end = today_start - timezone.timedelta(days=i-1)
        count = Session.objects.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).count()
        weekly_labels.append(day_start.strftime('%a'))
        weekly_data.append(count)

    # Recent activity
    recent_users = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]
    recent_sessions = Session.objects.select_related('user', 'task').order_by('-created_at')[:5]

    import json as _json
    return render(request, 'auth/admin_dashboard.html', {
        'total_users': total_users,
        'active_users_today': active_users_today,
        'new_users_today': new_users_today,
        'disabled_users': disabled_users,
        'total_tasks': total_tasks,
        'tasks_today': tasks_today,
        'completed_tasks': completed_tasks,
        'total_sessions': total_sessions,
        'sessions_today': sessions_today,
        'completed_sessions': completed_sessions,
        'pending_sessions': pending_sessions,
        'in_progress_sessions': in_progress_sessions,
        'cancelled_sessions': cancelled_sessions,
        'weekly_labels': _json.dumps(weekly_labels),
        'weekly_data': _json.dumps(weekly_data),
        'recent_users': recent_users,
        'recent_sessions': recent_sessions,
    })


@staff_member_required(login_url='login')
def admin_user_list(request):
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    return render(request, 'auth/admin_user_list.html', {'users': users})


@staff_member_required(login_url='login')
def admin_user_detail(request, pk):
    profile_user = get_object_or_404(User, pk=pk, is_staff=False)
    tasks = Task.objects.filter(user=profile_user).order_by('-created_at')
    sessions = Session.objects.filter(user=profile_user).order_by('-planned_start')[:10]
    return render(request, 'auth/admin_user_detail.html', {
        'profile_user': profile_user,
        'tasks': tasks,
        'sessions': sessions,
    })


@staff_member_required(login_url='login')
def admin_user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=False)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        status = 'enabled' if user.is_active else 'disabled'
        messages.success(request, f'Account "{user.username}" {status}.')
    return redirect('admin_user_list')


@staff_member_required(login_url='login')
def admin_category_list(request):
    categories = Category.objects.annotate(
        task_count=models.Count('task')
    ).order_by('name')
    return render(request, 'auth/admin_category_list.html', {'categories': categories})


@staff_member_required(login_url='login')
def admin_category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Category name is required.')
        elif Category.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Category "{name}" already exists.')
        else:
            Category.objects.create(name=name, description=description)
            messages.success(request, f'Category "{name}" created.')
            return redirect('admin_category_list')
    return render(request, 'auth/admin_category_form.html', {'mode': 'create'})


@staff_member_required(login_url='login')
def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Category name is required.')
        elif Category.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            messages.error(request, f'Category "{name}" already exists.')
        else:
            category.name = name
            category.description = description
            category.save()
            messages.success(request, f'Category updated.')
            return redirect('admin_category_list')
    return render(request, 'auth/admin_category_form.html', {
        'mode': 'edit', 'category': category
    })


@staff_member_required(login_url='login')
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        task_count = Task.objects.filter(category=category).count()
        if task_count > 0:
            messages.error(request, f'Cannot delete "{category.name}" — {task_count} task(s) are using it. Reassign them first.')
        else:
            category.delete()
            messages.success(request, f'Category "{category.name}" deleted.')
    return redirect('admin_category_list')


@staff_member_required(login_url='login')
def admin_task_list(request):
    user_filter = request.GET.get('user', '')
    category_filter = request.GET.get('category', '')
    tasks = Task.objects.select_related('user', 'category').order_by('-created_at')
    if user_filter:
        tasks = tasks.filter(user__username__icontains=user_filter)
    if category_filter:
        tasks = tasks.filter(category__id=category_filter)
    categories = Category.objects.all()
    paginator = Paginator(tasks, 15)
    page = request.GET.get('page', 1)
    tasks_page = paginator.get_page(page)
    return render(request, 'auth/admin_task_list.html', {
        'tasks': tasks_page,
        'categories': categories,
        'user_filter': user_filter,
        'category_filter': category_filter,
    })


@staff_member_required(login_url='login')
def admin_session_list(request):
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    sessions = Session.objects.select_related('user', 'task').order_by('-planned_start')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if user_filter:
        sessions = sessions.filter(user__username__icontains=user_filter)
    paginator = Paginator(sessions, 15)
    page = request.GET.get('page', 1)
    sessions_page = paginator.get_page(page)
    return render(request, 'auth/admin_session_list.html', {
        'sessions': sessions_page,
        'status_filter': status_filter,
        'user_filter': user_filter,
    })


# ========== Dashboard View ==========

@login_required
def dashboard(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Learning streak (up to 30 days)
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

    week_start = today_start - timezone.timedelta(days=today_start.weekday())
    week_minutes = Session.objects.filter(
        user=request.user,
        planned_start__gte=week_start,
        planned_start__lte=today_end,
    ).exclude(status__in=['cancelled', 'pending']).aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0

    today_minutes = Session.objects.filter(
        user=request.user,
        planned_start__gte=today_start,
        planned_start__lte=today_end,
    ).exclude(status__in=['cancelled', 'pending']).aggregate(
        total=Sum('actual_minutes')
    )['total'] or 0

    all_active = Task.objects.filter(user=request.user, is_active=True)
    active_tasks = [t for t in all_active if not t.is_completed()][:5]
    completed_count = len([t for t in all_active if t.is_completed()])

    recent_sessions = Session.objects.filter(
        user=request.user
    ).select_related('task').order_by('-planned_start')[:5]

    # Motivational message based on streak
    if streak == 0:
        motivation = "Start your first session today! 🌱"
    elif streak <= 3:
        motivation = "Great start! Keep the momentum going 🔥"
    elif streak <= 6:
        motivation = "You're on a roll! Don't break the chain 💪"
    elif streak <= 13:
        motivation = f"{streak} days strong! You're building a great habit 🚀"
    else:
        motivation = f"Incredible {streak}-day streak! You're unstoppable ⚡"

    return render(request, 'dashboard.html', {
        'streak': streak,
        'week_minutes': week_minutes,
        'today_minutes': today_minutes,
        'active_tasks': active_tasks,
        'completed_count': completed_count,
        'recent_sessions': recent_sessions,
        'motivation': motivation,
    })


# ========== Statistics View ==========

@login_required
def statistics(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # All completed/in-progress sessions for this user
    valid_sessions = Session.objects.filter(
        user=request.user
    ).exclude(status__in=['cancelled', 'pending'])

    # Summary numbers
    total_minutes = valid_sessions.aggregate(t=Sum('actual_minutes'))['t'] or 0
    total_sessions = Session.objects.filter(user=request.user).count()
    completed_sessions = Session.objects.filter(user=request.user, status='completed').count()
    avg_quality = valid_sessions.exclude(completion_percent=0).aggregate(
        a=Sum('completion_percent')
    )['a'] or 0
    quality_count = valid_sessions.exclude(completion_percent=0).count()
    avg_quality = round(avg_quality / quality_count) if quality_count else 0

    # Last 7 days — minutes per day
    weekly_labels = []
    weekly_data = []
    for i in range(6, -1, -1):
        day_start = today_start - timezone.timedelta(days=i)
        day_end = today_end - timezone.timedelta(days=i)
        mins = valid_sessions.filter(
            planned_start__gte=day_start,
            planned_start__lte=day_end,
        ).aggregate(t=Sum('actual_minutes'))['t'] or 0
        weekly_labels.append(day_start.strftime('%a'))
        weekly_data.append(mins)

    # Minutes by category
    category_labels = []
    category_data = []
    for cat in Category.objects.all():
        mins = valid_sessions.filter(task__category=cat).aggregate(
            t=Sum('actual_minutes')
        )['t'] or 0
        if mins > 0:
            category_labels.append(cat.name)
            category_data.append(mins)
    # Uncategorised
    uncategorised = valid_sessions.filter(task__category__isnull=True).aggregate(
        t=Sum('actual_minutes')
    )['t'] or 0
    if uncategorised > 0:
        category_labels.append('Uncategorised')
        category_data.append(uncategorised)

    # Per-task stats
    tasks = Task.objects.filter(user=request.user, is_active=True)
    task_stats = []
    for t in tasks:
        task_stats.append({
            'title': t.title,
            'category': t.category,
            'pct': t.progress_percent(),
            'actual': t.total_actual_minutes(),
            'target': t.target_minutes,
            'extra': t.extra_minutes(),
            'avg_quality': t.average_quality(),
            'streak': t.recent_streak(),
        })
    task_stats.sort(key=lambda x: x['pct'], reverse=True)

    # Recent 10 sessions for the table
    recent_sessions = Session.objects.filter(
        user=request.user
    ).select_related('task').order_by('-planned_start')[:10]

    import json as _json
    return render(request, 'statistics.html', {
        'total_minutes': total_minutes,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'avg_quality': avg_quality,
        'weekly_labels': _json.dumps(weekly_labels),
        'weekly_data': _json.dumps(weekly_data),
        'category_labels': _json.dumps(category_labels),
        'category_data': _json.dumps(category_data),
        'task_stats': task_stats,
        'recent_sessions': recent_sessions,
    })


# ========== Progress View ==========

@login_required
def progress_list(request):
    tasks = Task.objects.filter(user=request.user, is_active=True).order_by('-created_at')
    pending = [t for t in tasks if not t.is_completed()]
    done = [t for t in tasks if t.is_completed()]
    return render(request, 'progress/progress_list.html', {
        'pending': pending,
        'done': done,
    })


# ========== Task Views ==========

@login_required
def task_list(request):
    active_tasks = Task.objects.filter(user=request.user, is_active=True)
    in_progress = [t for t in active_tasks if t.progress_percent() < 100]
    completed = [t for t in active_tasks if t.progress_percent() >= 100]

    paginator = Paginator(in_progress, 8)
    page = request.GET.get('page', 1)
    in_progress_page = paginator.get_page(page)

    return render(request, 'sessions/task_list.html', {
        'in_progress': in_progress_page,
        'completed': completed,
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
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, 'sessions/task_form.html', {'form': form, 'editing': True, 'task': task})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
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

    # Auto-update pending sessions to in_progress if start time has passed
    Session.objects.filter(
        user=request.user,
        status='pending',
        planned_start__lte=now
    ).update(status='in_progress')

    from django.db.models import Case, When, IntegerField
    sessions = Session.objects.filter(user=request.user)
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Order: in_progress first, then pending, then completed/cancelled, newest first
    sessions = sessions.annotate(
        status_order=Case(
            When(status='in_progress', then=0),
            When(status='pending', then=1),
            When(status='completed', then=2),
            When(status='cancelled', then=3),
            default=4,
            output_field=IntegerField(),
        )
    ).order_by('status_order', '-planned_start')

    paginator = Paginator(sessions, 10)
    page = request.GET.get('page', 1)
    sessions_page = paginator.get_page(page)

    return render(request, 'sessions/session_list.html', {
        'sessions': sessions_page,
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
        return JsonResponse({'error': 'This session has not started yet.'}, status=400)

    try:
        data = json.loads(request.body)
        actual_minutes = int(data.get('actual_minutes', session.actual_minutes))
        completion_percent = int(data.get('completion_percent', session.completion_percent))
        notes = data.get('notes', session.notes)
        mark_complete = data.get('mark_complete', False)

        if actual_minutes == 0:
            return JsonResponse({'error': 'Please enter actual time spent before saving.'}, status=400)
        if actual_minutes < 0:
            return JsonResponse({'error': 'Time cannot be negative.'}, status=400)

        max_minutes = session.planned_minutes() * 3
        if actual_minutes > max_minutes:
            return JsonResponse({'error': f'Time too high. Max allowed: {max_minutes} min.'}, status=400)
        if not (0 <= completion_percent <= 100):
            return JsonResponse({'error': 'Quality must be between 0 and 100.'}, status=400)

        session.actual_minutes = actual_minutes
        session.completion_percent = completion_percent
        session.notes = notes
        session.status = 'completed' if mark_complete else 'in_progress'
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

        conflicts = Session.objects.filter(
            user=request.user,
            planned_start__lt=new_end,
            planned_end__gt=new_start,
        ).exclude(status='cancelled').exclude(pk=pk)
        if conflicts.exists():
            return JsonResponse({'error': 'This time slot conflicts with another session.'}, status=400)

        session.planned_start = new_start
        session.planned_end = new_end
        # Save time changes first (bug fix: was missing this save)
        session.save()

        # Then update status if needed
        now = timezone.now()
        if session.status == 'pending' and new_start <= now:
            session.status = 'in_progress'
            session.save(update_fields=['status'])

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
