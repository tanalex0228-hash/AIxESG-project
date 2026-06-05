from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.index, name="index"),
    path("create/<str:item_type>/", views.create_item, name="create"),
]
