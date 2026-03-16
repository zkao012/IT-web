from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import Task, Session, Category


# =====================================================================
# Model Tests
# =====================================================================

class CategoryModelTest(TestCase):

    def test_category_str(self):
        cat = Category.objects.create(name='Study')
        self.assertEqual(str(cat), 'Study')


class TaskModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Study')
        self.task = Task.objects.create(
            user=self.user,
            title='Test Task',
            target_minutes=60,
            category=self.category,
        )

    def _make_session(self, actual_minutes, status='completed'):
        now = timezone.now()
        return Session.objects.create(
            task=self.task,
            user=self.user,
            planned_start=now - timedelta(hours=1),
            planned_end=now,
            actual_minutes=actual_minutes,
            status=status,
        )

    def test_task_str(self):
        self.assertEqual(str(self.task), 'Test Task')

    def test_progress_percent_zero_with_no_sessions(self):
        self.assertEqual(self.task.progress_percent(), 0)

    def test_progress_percent_partial(self):
        self._make_session(30)
        self.assertEqual(self.task.progress_percent(), 50)

    def test_progress_capped_at_100(self):
        self._make_session(120)
        self.assertEqual(self.task.progress_percent(), 100)

    def test_extra_minutes_zero_when_under_target(self):
        self._make_session(30)
        self.assertEqual(self.task.extra_minutes(), 0)

    def test_extra_minutes_calculated_correctly(self):
        self._make_session(90)
        self.assertEqual(self.task.extra_minutes(), 30)

    def test_is_completed_false_when_under_100(self):
        self._make_session(30)
        self.assertFalse(self.task.is_completed())

    def test_is_completed_true_when_at_100(self):
        self._make_session(60)
        self.assertTrue(self.task.is_completed())

    def test_cancelled_sessions_excluded_from_progress(self):
        self._make_session(60, status='cancelled')
        self.assertEqual(self.task.progress_percent(), 0)

    def test_pending_sessions_excluded_from_progress(self):
        self._make_session(60, status='pending')
        self.assertEqual(self.task.progress_percent(), 0)

    def test_total_actual_minutes_sums_valid_sessions(self):
        self._make_session(30)
        self._make_session(20)
        self._make_session(10, status='cancelled')  # should be excluded
        self.assertEqual(self.task.total_actual_minutes(), 50)

    def test_average_quality_calculated(self):
        now = timezone.now()
        Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now - timedelta(hours=1), planned_end=now,
            actual_minutes=30, completion_percent=80, status='completed'
        )
        Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now - timedelta(hours=2), planned_end=now - timedelta(hours=1),
            actual_minutes=30, completion_percent=60, status='completed'
        )
        self.assertEqual(self.task.average_quality(), 70)


class SessionModelTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.task = Task.objects.create(user=self.user, title='Task', target_minutes=60)

    def test_planned_minutes_calculated_correctly(self):
        now = timezone.now()
        session = Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now,
            planned_end=now + timedelta(minutes=90),
            status='pending',
        )
        self.assertEqual(session.planned_minutes(), 90)

    def test_session_str_contains_task_title(self):
        now = timezone.now()
        session = Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now,
            planned_end=now + timedelta(hours=1),
            status='pending',
        )
        self.assertIn('Task', str(session))

    def test_session_default_status_is_pending(self):
        now = timezone.now()
        session = Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now,
            planned_end=now + timedelta(hours=1),
        )
        self.assertEqual(session.status, 'pending')


# =====================================================================
# View Tests — Access Control
# =====================================================================

class AuthViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.admin = User.objects.create_superuser(username='admin', password='adminpass123', email='admin@test.com')

    def test_login_page_accessible(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    def test_login_redirects_to_dashboard_on_success(self):
        response = self.client.post('/login/', {
            'username': 'testuser', 'password': 'testpass123'
        })
        self.assertRedirects(response, '/dashboard/')

    def test_login_redirects_admin_to_admin_dashboard(self):
        response = self.client.post('/login/', {
            'username': 'admin', 'password': 'adminpass123'
        })
        self.assertRedirects(response, '/admin-dashboard/')

    def test_login_fails_with_wrong_password(self):
        response = self.client.post('/login/', {
            'username': 'testuser', 'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_register_creates_user(self):
        response = self.client.post('/register/', {
            'email': 'new@test.com',
            'username': 'newuser',
            'password1': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout_redirects_to_login(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')


class TaskViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Study')
        self.client.login(username='testuser', password='testpass123')

    def test_task_list_requires_login(self):
        self.client.logout()
        response = self.client.get('/tasks/')
        self.assertRedirects(response, '/login/?next=/tasks/')

    def test_task_list_accessible_when_logged_in(self):
        response = self.client.get('/tasks/')
        self.assertEqual(response.status_code, 200)

    def test_create_task(self):
        response = self.client.post('/tasks/create/', {
            'title': 'New Task',
            'category': self.category.pk,
            'description': 'Test',
            'target_minutes': 60,
        })
        self.assertRedirects(response, '/tasks/')
        self.assertTrue(Task.objects.filter(title='New Task', user=self.user).exists())

    def test_cannot_access_other_users_task(self):
        other_user = User.objects.create_user(username='other', password='pass123')
        task = Task.objects.create(user=other_user, title='Other Task', target_minutes=60)
        response = self.client.post(f'/tasks/{task.pk}/delete/')
        # Should not delete the task
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())


class SessionViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.task = Task.objects.create(user=self.user, title='Task', target_minutes=60)
        self.client.login(username='testuser', password='testpass123')

    def test_session_list_requires_login(self):
        self.client.logout()
        response = self.client.get('/sessions/')
        self.assertRedirects(response, '/login/?next=/sessions/')

    def test_session_list_accessible(self):
        response = self.client.get('/sessions/')
        self.assertEqual(response.status_code, 200)

    def test_session_book_get(self):
        response = self.client.get('/sessions/book/')
        self.assertEqual(response.status_code, 200)

    def test_session_progress_update_via_ajax(self):
        import json
        now = timezone.now()
        session = Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now - timedelta(hours=1),
            planned_end=now,
            status='in_progress',
        )
        response = self.client.post(
            f'/sessions/{session.pk}/progress/',
            data=json.dumps({
                'actual_minutes': 45,
                'completion_percent': 80,
                'notes': 'Good session',
                'mark_complete': False,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        session.refresh_from_db()
        self.assertEqual(session.actual_minutes, 45)

    def test_cancel_session(self):
        now = timezone.now()
        session = Session.objects.create(
            task=self.task, user=self.user,
            planned_start=now + timedelta(hours=1),
            planned_end=now + timedelta(hours=2),
            status='pending',
        )
        response = self.client.post(f'/sessions/{session.pk}/cancel/')
        session.refresh_from_db()
        self.assertEqual(session.status, 'cancelled')


class AdminViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', password='adminpass123', email='a@test.com')
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='admin', password='adminpass123')

    def test_admin_dashboard_accessible_to_staff(self):
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_blocked_for_regular_user(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/admin-dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_admin_user_list_accessible(self):
        response = self.client.get('/manage/users/')
        self.assertEqual(response.status_code, 200)

    def test_admin_category_list_accessible(self):
        response = self.client.get('/manage/categories/')
        self.assertEqual(response.status_code, 200)

    def test_disable_user_account(self):
        response = self.client.post(f'/manage/users/{self.user.pk}/toggle/')
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_enable_user_account(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(f'/manage/users/{self.user.pk}/toggle/')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_create_category(self):
        response = self.client.post('/manage/categories/create/', {
            'name': 'Programming',
            'description': 'Coding tasks',
        })
        self.assertTrue(Category.objects.filter(name='Programming').exists())

    def test_cannot_delete_category_with_tasks(self):
        cat = Category.objects.create(name='InUse')
        Task.objects.create(user=self.user, title='T', target_minutes=60, category=cat)
        self.client.post(f'/manage/categories/{cat.pk}/delete/')
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

    def test_can_delete_empty_category(self):
        cat = Category.objects.create(name='Empty')
        self.client.post(f'/manage/categories/{cat.pk}/delete/')
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())
