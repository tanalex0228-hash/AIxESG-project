from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("industry/<str:industry_name>/", views.industry_detail, name="industry_detail"),
]
urlpatterns += [path("intro/", views.intro, name="intro")]
