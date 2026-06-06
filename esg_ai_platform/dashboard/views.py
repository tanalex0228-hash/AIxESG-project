from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user
from reports.models import Report


def intro(request):
    return render(request, "dashboard/intro.html")


@login_required
def index(request):
    organization = get_user_organization(request.user)
    if is_system_admin_user(request.user):
        reports = Report.objects.all().select_related("analysis_result", "organization")
        public_reports = reports.filter(status="completed")
    elif is_individual_user(request.user):
        reports = Report.objects.none()
        public_reports = Report.objects.filter(status="completed").select_related("analysis_result", "organization")
    else:
        reports = Report.objects.filter(organization=organization).select_related("analysis_result", "organization") if organization else Report.objects.none()
        public_reports = Report.objects.none()
    latest_result = None
    latest_report = reports.first() if reports else None
    if latest_report:
        latest_result = getattr(latest_report, "analysis_result", None)
    return render(
        request,
        "dashboard/index.html",
        {
            "organization": organization,
            "reports": reports[:8],
            "public_reports": public_reports[:20],
            "latest_report": latest_report,
            "latest_result": latest_result,
            "is_individual": is_individual_user(request.user),
            "is_system_admin": is_system_admin_user(request.user),
        },
    )
