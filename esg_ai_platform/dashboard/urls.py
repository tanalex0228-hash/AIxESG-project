from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [path("", views.index, name="index")]
urlpatterns += [path("intro/", views.intro, name="intro")]
