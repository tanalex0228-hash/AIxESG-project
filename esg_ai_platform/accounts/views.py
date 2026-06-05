from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(request=request)
            login(request, user)
            messages.success(request, "註冊完成，系統已保留註冊與操作紀錄。")
            return redirect("dashboard:index")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})
