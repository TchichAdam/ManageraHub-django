from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


def home(request):
    return render(request, "home.html")


def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_dashboard")

    error_message = None

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)

        if user and user.is_staff:
            login(request, user)
            return redirect("admin_dashboard")

        error_message = "Invalid admin credentials. Please try again."

    return render(request, "admin_login.html", {"error_message": error_message})


@login_required(login_url="/admin/login")
def admin_dashboard_view(request):
    if not request.user.is_staff:
        return redirect("/admin/login")

    return render(request, "admin_dashboard.html")
