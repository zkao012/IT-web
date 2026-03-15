from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('auth_app.urls')),
    path('booking/', include('booking_app.urls')),
    path('progress/', include('progress_app.urls')),
]