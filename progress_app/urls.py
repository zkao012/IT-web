from django.urls import path
from . import views

app_name = "progress_app"

urlpatterns = [
    path("", views.progress_list, name="list"),
    path("add/", views.progress_add, name="add"),
    path("edit/<int:pk>/", views.progress_edit, name="edit"),
    path("delete/<int:pk>/", views.progress_delete, name="delete"),
    path("done/<int:pk>/", views.mark_done, name="done"),
]