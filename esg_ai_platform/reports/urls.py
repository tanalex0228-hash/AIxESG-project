from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_list, name="list"),
    path("upload/", views.upload_report, name="upload"),
    path("compare/", views.compare_reports, name="compare"),
    path("<int:pk>/status/", views.report_status, name="status"),
    path("<int:pk>/status.json", views.report_status_json, name="status_json"),
    path("<int:pk>/", views.report_detail, name="detail"),
]
