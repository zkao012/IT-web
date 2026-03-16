from django.apps import AppConfig


class BookingAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'booking_app'

    def ready(self):
        from .models import Category
        try:
            Category.create_default_categories()
        except:
            pass