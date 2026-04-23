from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect

from .forms import RegisterForm, EditProfileForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    next_page = "clubs:home"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("clubs:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cuenta creada. Bienvenido a Lectorium!")
            return redirect("clubs:home")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    user = request.user

    from apps.clubs.models import ClubStatus
    active_statuses = [
        ClubStatus.OPEN, ClubStatus.READING, ClubStatus.SUBMISSION,
        ClubStatus.REVIEW, ClubStatus.DISCUSSION,
    ]
    active_memberships = list(
        user.memberships.filter(
            is_active=True,
            club__status__in=active_statuses,
        ).select_related("club", "club__book")
    )

    reports = list(
        user.reports.select_related("club", "club__book").prefetch_related("reactions")
    )

    context = {
        "active_memberships": active_memberships,
        "active_clubs_count": len(active_memberships),
        "reports": reports,
        "total_reports": len(reports),
    }
    return render(request, "accounts/profile.html", context)


@login_required
def edit_profile_view(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("accounts:profile")
    else:
        form = EditProfileForm(instance=request.user)

    return render(request, "accounts/edit_profile.html", {"form": form})
