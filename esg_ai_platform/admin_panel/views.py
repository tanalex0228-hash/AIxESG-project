from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.utils import user_has_admin_access
from benchmarks.models import BenchmarkBestPractice, BenchmarkCompany
from gri.models import GRICheckItem, GRIDisclosure, ScoringRule, ScoringWeight
from rag.models import RetrievalLog
from reports.models import AnalysisJob

from .forms import (
    BenchmarkBestPracticeForm,
    BenchmarkCompanyForm,
    GRICheckItemForm,
    GRIDisclosureForm,
    ScoringRuleForm,
    ScoringWeightForm,
)


def _require_admin(request):
    if not user_has_admin_access(request.user):
        messages.error(request, "沒有管理權限。")
        return False
    return True


@login_required
def index(request):
    if not _require_admin(request):
        return redirect("dashboard:index")
    context = {
        "disclosures": GRIDisclosure.objects.select_related("standard").all()[:20],
        "check_items": GRICheckItem.objects.select_related("disclosure").all()[:20],
        "weights": ScoringWeight.objects.select_related("disclosure").all(),
        "rules": ScoringRule.objects.select_related("disclosure").all()[:20],
        "companies": BenchmarkCompany.objects.all()[:20],
        "best_practices": BenchmarkBestPractice.objects.select_related("company").all()[:20],
        "retrieval_logs": RetrievalLog.objects.all()[:20],
        "analysis_jobs": AnalysisJob.objects.select_related("report").all()[:20],
    }
    return render(request, "admin_panel/index.html", context)


@login_required
def create_item(request, item_type):
    if not _require_admin(request):
        return redirect("dashboard:index")
    form_map = {
        "disclosure": GRIDisclosureForm,
        "check-item": GRICheckItemForm,
        "weight": ScoringWeightForm,
        "rule": ScoringRuleForm,
        "benchmark-company": BenchmarkCompanyForm,
        "best-practice": BenchmarkBestPracticeForm,
    }
    form_class = form_map[item_type]
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "資料已建立。")
        return redirect("admin_panel:index")
    return render(request, "admin_panel/form.html", {"form": form, "item_type": item_type})
