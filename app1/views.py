from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from django.http import JsonResponse
from django.core.mail import send_mail
from .emails import send_html_email
from .forms import CandidateProfileForm, CompanyProfileForm, JobApplicationForm, JobOfferFilterForm, JobOfferForm, CompanyJobFilterForm, CompanyApplicationFilterForm
from .models import CandidateProfile, CompanyProfile, JobApplication, JobOffer, Post, Comment, Follow, QuizResult
from . import quizzes

DEFAULT_CANDIDATE_DASHBOARD_URL = "/candidate/dashboard/"
DEFAULT_COMPANY_DASHBOARD_URL = "/company/dashboard"
User = get_user_model()


def home(request):
    return render(request, "home.html")


def admin_login_view(request):
    next_url = request.GET.get("next", "").strip()
    signin_url = reverse("signin")
    if next_url:
        return redirect(f"{signin_url}?next={next_url}")
    return redirect(signin_url)


def admin_dashboard_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("/admin/")
    return redirect(reverse("signin"))


def admin_logout_view(request):
    logout(request)
    return redirect("/signin")


def account_logout_view(request):
    logout(request)
    return redirect(reverse("candidate_signin"))


def _build_full_name(first_name, last_name):
    return " ".join(part for part in [first_name.strip(), last_name.strip()] if part).strip()


def _candidate_dashboard_url():
    return reverse("candidate_dashboard")


def _create_candidate_profile(user, **extra_fields):
    defaults = {
        "phone_number": extra_fields.get("phone_number", "").strip(),
        "address": extra_fields.get("address", "").strip(),
        "city": extra_fields.get("city", "").strip(),
        "country": extra_fields.get("country", "").strip(),
        "headline": extra_fields.get("headline", "").strip(),
    }
    profile, created = CandidateProfile.objects.get_or_create(user=user, defaults=defaults)
    if not created:
        changed = False
        updated_fields = []
        for field_name, value in defaults.items():
            if value and not getattr(profile, field_name):
                setattr(profile, field_name, value)
                changed = True
                updated_fields.append(field_name)
        if changed:
            profile.save(update_fields=updated_fields)
    return profile


def _create_company_profile(user, **extra_fields):
    defaults = {
        "company_name": extra_fields.get("company_name", "").strip(),
        "phone_number": extra_fields.get("phone_number", "").strip(),
        "city": extra_fields.get("city", "").strip(),
        "country": extra_fields.get("country", "").strip(),
        "industry": extra_fields.get("industry", "").strip(),
        "company_size": extra_fields.get("company_size", "").strip(),
        "website": extra_fields.get("website", "").strip(),
        "description": extra_fields.get("description", "").strip(),
        "ice": extra_fields.get("ice", "").strip() if extra_fields.get("ice") else None,
        "rc_number": extra_fields.get("rc_number", "").strip() if extra_fields.get("rc_number") else None,
        "legal_document": extra_fields.get("legal_document"),
    }
    profile, created = CompanyProfile.objects.get_or_create(user=user, defaults=defaults)
    if not created:
        changed = False
        updated_fields = []
        for field_name, value in defaults.items():
            # Treat FileField correctly
            if value is not None and not getattr(profile, field_name):

                setattr(profile, field_name, value)
                changed = True
                updated_fields.append(field_name)
        if changed:
            profile.save(update_fields=updated_fields)
    return profile


def _ensure_candidate_profile(user):
    if (
        user.is_authenticated
        and not user.is_staff
        and not hasattr(user, "candidate_profile")
        and not hasattr(user, "company_profile")
    ):
        return _create_candidate_profile(user, headline=user.get_full_name().strip())
    return getattr(user, "candidate_profile", None)


def _is_candidate_user(user):
    return user.is_authenticated and not user.is_staff and hasattr(user, "candidate_profile")


def _candidate_redirect_response(request):
    signin_url = reverse("candidate_signin")
    if not request.user.is_authenticated:
        return redirect(f"{signin_url}?next={request.path}")
    if request.user.is_staff:
        return redirect("/admin/")
    return redirect(reverse("signin"))


def _candidate_nav_items():
    return [
        {"key": "dashboard", "label": "Home", "url": reverse("candidate_dashboard")},
        {"key": "feed", "label": "Feed", "url": reverse("candidate_feed")},
        {"key": "network", "label": "Network", "url": reverse("candidate_network")},
        {"key": "profile", "label": "My Profile", "url": reverse("candidate_profile")},
        {"key": "jobs", "label": "Job Offers", "url": reverse("candidate_job_offers")},
        {"key": "quizzes", "label": "Skills Quiz", "url": reverse("candidate_quizzes")},
        {"key": "settings", "label": "Settings", "url": reverse("candidate_settings")},
        {"key": "logout", "label": "Logout", "url": reverse("account_logout")},
    ]


def _candidate_base_context(request, active_key):
    profile = _ensure_candidate_profile(request.user)
    application_count = JobApplication.objects.filter(candidate=request.user).count()
    saved_docs_count = sum(
        1
        for field in [profile.cv_file, profile.cover_letter_file]
        if field
    )
    saved_docs_count += profile.certifications.count()
    initials = "".join(
        part[0].upper() for part in (request.user.first_name, request.user.last_name) if part
    )[:2] or request.user.username[:2].upper()
    return {
        "active_section": active_key,
        "candidate_nav_items": _candidate_nav_items(),
        "candidate_profile": profile,
        "candidate_display_name": profile.display_name,
        "candidate_completion_percent": profile.completion_percent,
        "candidate_initials": initials,
        "candidate_stats": {
            "applications": application_count,
            "saved_docs": saved_docs_count,
            "recent_jobs": JobOffer.objects.filter(is_active=True).count(),
        },
    }


def _company_nav_items():
    return [
        {"key": "dashboard", "label": "Home", "url": reverse("company_dashboard")},
        {"key": "jobs", "label": "My Jobs", "url": reverse("company_jobs")},
        {"key": "applications", "label": "Applications", "url": reverse("company_applications")},
        {"key": "profile", "label": "Profile", "url": reverse("company_profile")},
        {"key": "logout", "label": "Logout", "url": reverse("account_logout")},
    ]


def _is_company_user(user):
    return user.is_authenticated and not user.is_staff and hasattr(user, "company_profile")


def _company_redirect_response(request):
    signin_url = reverse("company_signin")
    if not request.user.is_authenticated:
        return redirect(f"{signin_url}?next={request.path}")
    if request.user.is_staff:
        return redirect("/admin/")
    return redirect(reverse("signin"))


def _company_base_context(request, active_key):
    profile = request.user.company_profile
    company_name = profile.company_name or request.user.get_full_name() or request.user.username
    company_jobs = JobOffer.objects.filter(company_name=company_name)
    company_applications = JobApplication.objects.filter(job_offer__company_name=company_name)
    initials = "".join(word[0].upper() for word in company_name.split() if word)[:2] or "CO"
    return {
        "active_section": active_key,
        "company_nav_items": _company_nav_items(),
        "company_profile": profile,
        "company_display_name": company_name,
        "company_initials": initials,
        "company_stats": {
            "posted_jobs": company_jobs.filter(is_active=True).count(),
            "total_applications": company_applications.count(),
            "pending_applications": company_applications.filter(status="sent").count(),
            "accepted_applications": company_applications.filter(status="accepted").count(),
        },
    }


def company_dashboard_view(request):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    if not request.user.company_profile.is_approved:
        return redirect(reverse("company_pending_approval"))
    ctx = _company_base_context(request, "dashboard")
    company_name = ctx["company_display_name"]
    ctx["recent_applications"] = (
        JobApplication.objects.filter(job_offer__company_name=company_name)
        .select_related("job_offer")
        .order_by("-submitted_at")[:5]
    )
    ctx["active_jobs"] = (
        JobOffer.objects.filter(company_name=company_name, is_active=True)
        .prefetch_related("applications")
        .order_by("-created_at")[:5]
    )
    return render(request, "company/dashboard.html", ctx)



def _signin_context(**extra):
    context = {
        "social_auth_enabled": settings.HAS_ALLAUTH,
        "google_auth_enabled": getattr(settings, "GOOGLE_AUTH_CONFIGURED", False) and settings.HAS_ALLAUTH,
        "github_auth_enabled": getattr(settings, "GITHUB_AUTH_CONFIGURED", False) and settings.HAS_ALLAUTH,
    }
    context.update(extra)
    return context


def candidate_register_view(request):
    error_message = None
    success_message = None

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        city = request.POST.get("city", "").strip()
        country = request.POST.get("country", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("password_confirm", "")

        if password != confirm_password:
            error_message = "Passwords do not match. Please try again."
        elif not email:
            error_message = "Email is required."
        elif User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            error_message = "An account with this email already exists."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error_message = " ".join(exc.messages)
            else:
                from django.db import IntegrityError
                try:
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    _create_candidate_profile(
                        user,
                        phone_number=phone,
                        city=city,
                        country=country,
                        headline=_build_full_name(first_name, last_name),
                    )
                    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                    return redirect(_candidate_dashboard_url())
                except IntegrityError:
                    # Double-submit race condition (both requests passed validation concurrently).
                    # Fetch the concurrently created user, authenticate, and redirect to the dashboard.
                    user = User.objects.get(username=email)
                    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                    return redirect(_candidate_dashboard_url())

    return render(
        request,
        "candidate_register.html",
        {
            "error_message": error_message,
            "success_message": success_message,
        },
    )


def company_register_view(request):
    error_message = None
    success_message = None

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        industry = request.POST.get("industry", "").strip()
        industry_other = request.POST.get("industry_other", "").strip()
        company_size = request.POST.get("company_size", "").strip()
        country = request.POST.get("country", "").strip()
        city = request.POST.get("city", "").strip()
        website = request.POST.get("website", "").strip()
        description = request.POST.get("description", "").strip()
        first_name = request.POST.get("admin_first", "").strip()
        last_name = request.POST.get("admin_last", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("password_confirm", "")

        # Legal Verification fields
        ice = request.POST.get("ice", "").strip()
        rc_number = request.POST.get("rc_number", "").strip()
        legal_document = request.FILES.get("legal_document")

        if password != confirm_password:
            error_message = "Passwords do not match. Please try again."
        elif not email:
            error_message = "Email is required."
        elif not company_name:
            error_message = "Company name is required."
        elif ice and (not ice.isdigit() or len(ice) != 15):
            error_message = "The ICE number must contain exactly 15 digits."
        elif User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            error_message = "An account with this email already exists."
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error_message = " ".join(exc.messages)
            else:
                from django.db import IntegrityError
                try:
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    resolved_industry = industry_other if industry == "Other" and industry_other else industry
                    _create_company_profile(
                        user,
                        company_name=company_name,
                        phone_number=phone,
                        city=city,
                        country=country,
                        industry=resolved_industry,
                        company_size=company_size,
                        website=website,
                        description=description,
                        ice=ice,
                        rc_number=rc_number,
                        legal_document=legal_document,
                    )
                    return redirect(reverse("company_pending_approval"))
                except IntegrityError:
                    # Double-submit race condition (both requests passed validation concurrently).
                    # Redirect to the pending approval success page so both viewports sync to the same success view.
                    return redirect(reverse("company_pending_approval"))

    return render(
        request,
        "company_register.html",
        {
            "error_message": error_message,
            "success_message": success_message,
        },
    )



def _signin_view(request, selected_role=None):
    error_message = None
    active_role = selected_role

    if request.method == "POST":
        active_role = request.POST.get("role", active_role or "candidate").strip().lower()
        if active_role not in {"candidate", "company"}:
            active_role = "candidate"

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_staff:
                login(request, user)
                next_url = request.GET.get("next", "").strip()
                return redirect(next_url or "/admin/")

            is_candidate = hasattr(user, "candidate_profile")
            is_company = hasattr(user, "company_profile")

            if active_role == "candidate" and is_company and not is_candidate:
                error_message = "This account is registered as a company. Please use the company sign in page."
            elif active_role == "company" and is_candidate and not is_company:
                error_message = "This account is registered as a candidate. Please use the candidate sign in page."
            elif is_company and not user.company_profile.is_approved:
                return redirect(reverse("company_pending_approval"))
            else:
                login(request, user)
                next_url = request.GET.get("next", "").strip()
                if active_role == "candidate":
                    if not is_candidate:
                        _create_candidate_profile(user, headline=user.get_full_name().strip())
                    return redirect(next_url or _candidate_dashboard_url())
                if not is_company:
                    _create_company_profile(user, company_name=user.get_full_name().strip() or user.username)
                return redirect(next_url or DEFAULT_COMPANY_DASHBOARD_URL)
        else:
            error_message = "Invalid email or password. Please try again."

    active_role = active_role or "candidate"
    return render(
        request,
        "signin.html",
        _signin_context(
            error_message=error_message,
            active_role=active_role,
            is_role_specific_page=selected_role in {"candidate", "company"},
            role_page_title="Candidate Sign In" if active_role == "candidate" else "Company Sign In",
            form_action=request.path,
        ),
    )


def signin_view(request):
    return _signin_view(request)


def candidate_signin_view(request):
    return _signin_view(request, selected_role="candidate")


def company_signin_view(request):
    return _signin_view(request, selected_role="company")


def candidate_dashboard_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    if request.GET.get("check_status") == "1":
        app_id = request.GET.get("app_id")
        try:
            app = JobApplication.objects.get(id=app_id, candidate=request.user)
            return JsonResponse({
                "status": app.status,
                "status_display": app.get_status_display(),
                "steps": app.progress_steps,
                "logs": app.live_activity_logs,
                "updated_at": app.updated_at.strftime("%d %b %Y à %H:%M")
            })
        except JobApplication.DoesNotExist:
            return JsonResponse({"error": "Candidature introuvable."}, status=404)

    profile = request.user.candidate_profile
    applications = JobApplication.objects.filter(candidate=request.user).select_related("job_offer")[:3]
    tracked_applications = (
        JobApplication.objects
        .filter(candidate=request.user)
        .select_related("job_offer")
        .order_by("-submitted_at")[:5]
    )
    recent_jobs = JobOffer.objects.filter(is_active=True)[:4]
    latest_quiz = QuizResult.objects.filter(candidate=request.user).first()
    context = _candidate_base_context(request, "dashboard")
    context.update(
        {
            "tracked_applications": tracked_applications,
            "latest_quiz": latest_quiz,
            "quiz_title": quizzes.QUIZ_TITLE,
            "quiz_subtitle": quizzes.QUIZ_SUBTITLE,
            "quiz_question_count": len(quizzes.QUIZ_QUESTIONS),
            "profile_missing_items": [
                label
                for label, ready in [
                    ("Phone number", bool(profile.phone_number)),
                    ("Region", bool(profile.address)),
                    ("Education", bool(profile.education_level)),
                    ("Skills", bool(profile.skills)),
                    ("Experience", bool(profile.experience_summary)),
                    ("CV upload", bool(profile.cv_file)),
                    ("Cover letter upload", bool(profile.cover_letter_file)),
                ]
                if not ready
            ],
            "applications": applications,
            "recent_jobs": recent_jobs,
        }
    )
    return render(request, "candidate/dashboard.html", context)


def candidate_profile_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    profile = request.user.candidate_profile
    if request.method == "POST":
        form = CandidateProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('candidate_profile')}?saved=1")
    else:
        form = CandidateProfileForm(instance=profile, user=request.user)

    context = _candidate_base_context(request, "profile")
    context.update(
        {
            "form": form,
            "saved": request.GET.get("saved") == "1",
        }
    )
    return render(request, "candidate/profile.html", context)


def candidate_job_offers_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    form = JobOfferFilterForm(request.GET or None)
    jobs = JobOffer.objects.filter(is_active=True)
    if form.is_valid():
        keyword = form.cleaned_data.get("keyword")
        city = form.cleaned_data.get("city")
        company = form.cleaned_data.get("company")
        job_type = form.cleaned_data.get("job_type")
        contract_type = form.cleaned_data.get("contract_type")
        experience_level = form.cleaned_data.get("experience_level")
        date_posted = form.cleaned_data.get("date_posted")

        if keyword:
            jobs = jobs.filter(
                Q(title__icontains=keyword)
                | Q(company_name__icontains=keyword)
                | Q(summary__icontains=keyword)
                | Q(requirements__icontains=keyword)
            )
        if city:
            jobs = jobs.filter(city__icontains=city)
        if company:
            jobs = jobs.filter(company_name__icontains=company)
        if job_type:
            jobs = jobs.filter(job_type=job_type)
        if contract_type:
            jobs = jobs.filter(contract_type=contract_type)
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        if date_posted:
            jobs = jobs.filter(posted_at__gte=timezone.now() - timedelta(days=int(date_posted)))

    context = _candidate_base_context(request, "jobs")
    context.update(
        {
            "filter_form": form,
            "jobs": jobs,
        }
    )
    return render(request, "candidate/jobs.html", context)


def candidate_job_detail_view(request, job_id):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    job = get_object_or_404(JobOffer, pk=job_id, is_active=True)
    existing_application = JobApplication.objects.filter(candidate=request.user, job_offer=job).first()
    context = _candidate_base_context(request, "jobs")
    context.update(
        {
            "job": job,
            "existing_application": existing_application,
            "application_success": request.GET.get("applied") == "1",
        }
    )
    return render(request, "candidate/job_detail.html", context)


def candidate_job_apply_view(request, job_id):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    job = get_object_or_404(JobOffer, pk=job_id, is_active=True)
    profile = request.user.candidate_profile
    existing_application = JobApplication.objects.filter(candidate=request.user, job_offer=job).first()
    if existing_application is not None:
        return redirect(f"{reverse('candidate_job_detail', args=[job.id])}?applied=1")

    if request.method == "POST":
        form = JobApplicationForm(request.POST, request.FILES, profile=profile)
        if form.is_valid():
            application = form.save(commit=False)
            application.candidate = request.user
            application.job_offer = job
            application.status = "sent"
            from django.db import IntegrityError
            try:
                application.save()
                return redirect(f"{reverse('candidate_job_detail', args=[job.id])}?applied=1")
            except IntegrityError:
                # Double-submit race condition: redirect to success detail view
                return redirect(f"{reverse('candidate_job_detail', args=[job.id])}?applied=1")
    else:
        form = JobApplicationForm(profile=profile)

    context = _candidate_base_context(request, "jobs")
    context.update(
        {
            "job": job,
            "form": form,
        }
    )
    return render(request, "candidate/job_apply.html", context)


def candidate_feed_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        image = request.FILES.get("image")
        video = request.FILES.get("video")
        location = request.POST.get("location", "").strip()
        tagged_company_id = request.POST.get("tagged_company", "").strip()
        tagged_users_ids = request.POST.getlist("tagged_users")

        if content or image or video or location or tagged_company_id or tagged_users_ids:
            tagged_company = None
            if tagged_company_id:
                try:
                    tagged_company = CompanyProfile.objects.get(pk=tagged_company_id)
                except CompanyProfile.DoesNotExist:
                    pass

            post = Post.objects.create(
                author=request.user,
                content=content,
                image=image,
                video=video,
                location=location or None,
                tagged_company=tagged_company
            )

            if tagged_users_ids:
                users_to_tag = User.objects.filter(id__in=tagged_users_ids)
                post.tagged_users.add(*users_to_tag)

        return redirect(reverse("candidate_feed"))

    # GET request
    query = request.GET.get("q", "").strip()
    hashtag = request.GET.get("hashtag", "").strip()
    posts = Post.objects.select_related("author", "tagged_company").prefetch_related(
        "likes", "comments", "comments__author", "tagged_users", "tagged_users__candidate_profile"
    ).all()
    
    if query:
        posts = posts.filter(
            Q(content__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query) |
            Q(author__username__icontains=query) |
            Q(author__candidate_profile__headline__icontains=query) |
            Q(author__company_profile__company_name__icontains=query) |
            Q(comments__content__icontains=query)
        ).distinct()

    if hashtag:
        if not hashtag.startswith("#"):
            hashtag = f"#{hashtag}"
        posts = posts.filter(content__icontains=hashtag)

    followed_user_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    suggestions = User.objects.exclude(id=request.user.id).exclude(id__in=followed_user_ids).filter(
        Q(candidate_profile__isnull=False) | Q(company_profile__isnull=False)
    ).select_related("candidate_profile", "company_profile")[:4]

    # AJAX Search suggestions endpoint
    if request.GET.get("suggest") == "1":
        query = request.GET.get("q", "").strip()
        suggestions_list = []
        if query:
            # 1. Matching posts
            matching_posts = Post.objects.filter(content__icontains=query).select_related("author")[:5]
            for p in matching_posts:
                author_name = p.author.get_full_name().strip() or p.author.username
                suggestions_list.append({
                    "type": "post",
                    "id": p.id,
                    "title": f"Publication de {author_name}",
                    "preview": p.content[:45] + "..." if len(p.content) > 45 else p.content,
                    "url": f"#post-{p.id}"
                })
            # 2. Matching tags
            for tag in ["#OFPPT", "#Laravel", "#Comptabilite", "#MongoDB", "#MoroccoTech"]:
                if query.lower() in tag.lower():
                    suggestions_list.append({
                        "type": "tag",
                        "title": tag,
                        "preview": "Tendance dans le flux",
                        "url": f"?hashtag={tag[1:]}"
                    })
        return JsonResponse({"suggestions": suggestions_list})

    # Pagination setup
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.template.loader import render_to_string

    paginator = Paginator(posts, 4)
    page_num = request.GET.get("page", 1)
    
    try:
        posts_page = paginator.page(page_num)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
            return JsonResponse({"html": "", "has_next": False})
        posts_page = paginator.page(paginator.num_pages)

    # Pre-populate dynamic fields on the current page's posts only (extremely optimized!)
    for post in posts_page:
        post.has_liked = post.likes.filter(id=request.user.id).exists()
        post.author_display_name = post.author.get_full_name().strip() or post.author.username
        if hasattr(post.author, "candidate_profile"):
            post.author_title = post.author.candidate_profile.headline or "Candidat"
            post.author_avatar = post.author.candidate_profile.profile_picture.url if post.author.candidate_profile.profile_picture else ""
        elif hasattr(post.author, "company_profile"):
            post.author_title = f"{post.author.company_profile.company_name} (Entreprise)"
            post.author_avatar = post.author.company_profile.logo.url if post.author.company_profile.logo else ""
        else:
            post.author_title = "Membre"
            post.author_avatar = ""

    # AJAX pagination endpoint
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.GET.get("ajax") == "1":
        html = render_to_string("candidate/posts_loop.html", {"posts": posts_page, "request": request})
        return JsonResponse({
            "html": html,
            "has_next": posts_page.has_next()
        })

    trending_tags = [
        {"name": "#OFPPT", "count": 142},
        {"name": "#Laravel", "count": 98},
        {"name": "#Comptabilite", "count": 75},
        {"name": "#MongoDB", "count": 54},
        {"name": "#MoroccoTech", "count": 118},
    ]

    all_companies = CompanyProfile.objects.all()
    all_members = User.objects.exclude(id=request.user.id).filter(
        Q(candidate_profile__isnull=False) | Q(company_profile__isnull=False)
    ).select_related("candidate_profile", "company_profile")

    context = _candidate_base_context(request, "feed")
    context.update({
        "posts": posts_page,
        "suggestions": suggestions,
        "trending_tags": trending_tags,
        "selected_hashtag": hashtag,
        "search_query": query,
        "all_companies": all_companies,
        "all_members": all_members,
    })
    return render(request, "candidate/feed.html", context)


def candidate_applications_view(request):
    return redirect(_candidate_dashboard_url())


def candidate_application_status_view(request):
    return redirect(_candidate_dashboard_url())


def candidate_quizzes_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    result = None
    reviewed_questions = None
    if request.method == "POST":
        score, total, reviewed_questions = quizzes.score_quiz(request.POST)
        result = QuizResult.objects.create(candidate=request.user, score=score, total=total)

    context = _candidate_base_context(request, "quizzes")
    context.update(
        {
            "quiz_title": quizzes.QUIZ_TITLE,
            "quiz_subtitle": quizzes.QUIZ_SUBTITLE,
            "questions": quizzes.QUIZ_QUESTIONS,
            "result": result,
            "reviewed_questions": reviewed_questions,
            "previous_results": QuizResult.objects.filter(candidate=request.user)[:5],
            "best_result": (
                QuizResult.objects.filter(candidate=request.user)
                .order_by("-score", "-taken_at")
                .first()
            ),
        }
    )
    return render(request, "candidate/quiz.html", context)


def candidate_network_view(request):
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    followed_user_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
    
    query = request.GET.get("q", "").strip()
    
    # Get all users (except current) who are either candidates or companies
    network_users = User.objects.exclude(id=request.user.id).filter(
        Q(candidate_profile__isnull=False) | Q(company_profile__isnull=False)
    ).select_related("candidate_profile", "company_profile")

    if query:
        network_users = network_users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(candidate_profile__headline__icontains=query) |
            Q(candidate_profile__city__icontains=query) |
            Q(company_profile__company_name__icontains=query) |
            Q(company_profile__industry__icontains=query) |
            Q(company_profile__city__icontains=query)
        )

    for user in network_users:
        user.is_followed = user.id in followed_user_ids
        user.display_name = user.get_full_name().strip() or user.username
        if hasattr(user, "candidate_profile"):
            user.role = "candidate"
            user.title = user.candidate_profile.headline or "Candidate"
            user.location = f"{user.candidate_profile.city}, {user.candidate_profile.country}" if user.candidate_profile.city else "Morocco"
            user.avatar = user.candidate_profile.profile_picture.url if user.candidate_profile.profile_picture else ""
        elif hasattr(user, "company_profile"):
            user.role = "company"
            user.title = f"{user.company_profile.industry} • {user.company_profile.company_size}"
            user.location = f"{user.company_profile.city}, {user.company_profile.country}" if user.company_profile.city else "Morocco"
            user.avatar = user.company_profile.logo.url if user.company_profile.logo else ""

    context = _candidate_base_context(request, "network")
    context.update({
        "network_users": network_users,
        "followed_user_ids": followed_user_ids,
        "search_query": query,
    })
    return render(request, "candidate/network.html", context)


def post_like_view(request, post_id):
    if not request.user.is_authenticated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return redirect(reverse("candidate_signin"))
    post = get_object_or_404(Post, pk=post_id)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    
    if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
        return JsonResponse({
            "liked": liked,
            "total_likes": post.total_likes,
        })
    return redirect(request.META.get("HTTP_REFERER", reverse("candidate_feed")))


def post_comment_view(request, post_id):
    if not request.user.is_authenticated:
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": "Unauthorized"}, status=401)
        return redirect(reverse("candidate_signin"))
    post = get_object_or_404(Post, pk=post_id)
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            comment = Comment.objects.create(post=post, author=request.user, content=content)
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
                return JsonResponse({
                    "success": True,
                    "author_name": comment.author.get_full_name().strip() or comment.author.username,
                    "author_avatar": comment.author.username[0].upper(),
                    "content": comment.content,
                    "created_at": comment.created_at.strftime("%d %b, %H:%M"),
                    "total_comments": post.comments.count(),
                })
    return redirect(request.META.get("HTTP_REFERER", reverse("candidate_feed")))


def toggle_follow_view(request, user_id):
    if not request.user.is_authenticated:
        return redirect(reverse("candidate_signin"))
    
    following_user = get_object_or_404(User, pk=user_id)
    follow_rel = Follow.objects.filter(follower=request.user, following=following_user)
    if follow_rel.exists():
        follow_rel.delete()
    else:
        Follow.objects.create(follower=request.user, following=following_user)
    return redirect(request.META.get("HTTP_REFERER", reverse("candidate_network")))


def candidate_settings_view(request):
    from django.contrib.auth import update_session_auth_hash
    _ensure_candidate_profile(request.user)
    if not _is_candidate_user(request.user):
        return _candidate_redirect_response(request)

    profile = request.user.candidate_profile
    password_error = None
    password_success = None
    visibility_success = None

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "update_visibility":
            is_public_val = request.POST.get("is_public") == "true"
            profile.is_public = is_public_val
            profile.save()
            visibility_success = "Profile visibility updated successfully."
        elif action == "change_password":
            old_password = request.POST.get("old_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            # Verify old password
            if not request.user.check_password(old_password):
                password_error = "Your current password was entered incorrectly."
            elif new_password != confirm_password:
                password_error = "The new passwords do not match."
            else:
                try:
                    validate_password(new_password, user=request.user)
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    password_success = "Your password was changed successfully."
                except ValidationError as e:
                    password_error = " ".join(e.messages)

    context = _candidate_base_context(request, "settings")
    context.update({
        "profile": profile,
        "password_error": password_error,
        "password_success": password_success,
        "visibility_success": visibility_success,
    })
    return render(request, "candidate/settings.html", context)


def password_reset_view(request):
    success = False
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        form = PasswordResetForm({"email": email})
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="registration/password_reset_email.html",
            )
        success = True

    return render(request, "signin.html", _signin_context(reset_success=success, active_role="candidate"))


def company_profile_view(request):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    if not request.user.company_profile.is_approved:
        return redirect(reverse("company_pending_approval"))
    profile = request.user.company_profile
    success = False
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = CompanyProfileForm(instance=profile)
    ctx = _company_base_context(request, "profile")
    ctx["form"] = form
    ctx["success"] = success
    return render(request, "company/profile.html", ctx)


def company_post_job_view(request):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    if not request.user.company_profile.is_approved:
        return redirect(reverse("company_pending_approval"))
    profile = request.user.company_profile
    if request.method == "POST":
        form = JobOfferForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company_name = profile.company_name
            job.save()
            return redirect(reverse("company_jobs"))
    else:
        form = JobOfferForm(initial={"country": profile.country or "Morocco", "city": profile.city})
    ctx = _company_base_context(request, "jobs")
    ctx["form"] = form
    return render(request, "company/post_job.html", ctx)


def company_jobs_view(request):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    if not request.user.company_profile.is_approved:
        return redirect(reverse("company_pending_approval"))
    ctx = _company_base_context(request, "jobs")
    company_name = ctx["company_display_name"]

    form = CompanyJobFilterForm(request.GET or None)
    jobs = (
        JobOffer.objects.filter(company_name=company_name)
        .prefetch_related("applications")
        .order_by("-created_at")
    )

    if form.is_valid():
        keyword = form.cleaned_data.get("keyword")
        job_type = form.cleaned_data.get("job_type")
        contract_type = form.cleaned_data.get("contract_type")
        experience_level = form.cleaned_data.get("experience_level")
        status = form.cleaned_data.get("status")
        date_posted = form.cleaned_data.get("date_posted")

        if keyword:
            jobs = jobs.filter(
                Q(title__icontains=keyword)
                | Q(summary__icontains=keyword)
                | Q(requirements__icontains=keyword)
            )
        if job_type:
            jobs = jobs.filter(job_type=job_type)
        if contract_type:
            jobs = jobs.filter(contract_type=contract_type)
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        if status == "active":
            jobs = jobs.filter(is_active=True)
        elif status == "inactive":
            jobs = jobs.filter(is_active=False)
        if date_posted:
            jobs = jobs.filter(
                created_at__gte=timezone.now() - timedelta(days=int(date_posted))
            )

    ctx["filter_form"] = form
    ctx["jobs"] = jobs
    return render(request, "company/jobs.html", ctx)


def company_job_edit_view(request, job_id):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    profile = request.user.company_profile
    job = get_object_or_404(JobOffer, pk=job_id, company_name=profile.company_name)
    success = False
    if request.method == "POST":
        form = JobOfferForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = JobOfferForm(instance=job)
    ctx = _company_base_context(request, "jobs")
    ctx["form"] = form
    ctx["job"] = job
    ctx["success"] = success
    return render(request, "company/job_edit.html", ctx)


def company_job_toggle_view(request, job_id):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    profile = request.user.company_profile
    job = get_object_or_404(JobOffer, pk=job_id, company_name=profile.company_name)
    job.is_active = not job.is_active
    job.save(update_fields=["is_active"])
    return redirect(reverse("company_jobs"))


def company_job_delete_view(request, job_id):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    profile = request.user.company_profile
    job = get_object_or_404(JobOffer, pk=job_id, company_name=profile.company_name)
    if request.method == "POST":
        job.delete()
    return redirect(reverse("company_jobs"))


def company_applications_view(request):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    if not request.user.company_profile.is_approved:
        return redirect(reverse("company_pending_approval"))
    ctx = _company_base_context(request, "applications")
    company_name = ctx["company_display_name"]

    form = CompanyApplicationFilterForm(request.GET or None)
    qs = JobApplication.objects.filter(
        job_offer__company_name=company_name
    ).select_related("job_offer")

    if form.is_valid():
        keyword = form.cleaned_data.get("keyword")
        status = form.cleaned_data.get("status")
        job_title = form.cleaned_data.get("job_title")
        date_received = form.cleaned_data.get("date_received")

        if keyword:
            qs = qs.filter(
                Q(full_name__icontains=keyword)
                | Q(email__icontains=keyword)
            )
        if status:
            qs = qs.filter(status=status)
        if job_title:
            qs = qs.filter(job_offer__title__icontains=job_title)
        if date_received:
            qs = qs.filter(
                submitted_at__gte=timezone.now() - timedelta(days=int(date_received))
            )

    ctx["filter_form"] = form
    ctx["applications"] = qs.order_by("-submitted_at")
    ctx["status_choices"] = JobApplication.STATUS_CHOICES
    return render(request, "company/applications.html", ctx)


def company_application_detail_view(request, application_id):
    if not _is_company_user(request.user):
        return _company_redirect_response(request)
    profile = request.user.company_profile
    application = get_object_or_404(
        JobApplication.objects.select_related("job_offer"),
        pk=application_id,
        job_offer__company_name=profile.company_name,
    )
    if request.method == "POST":
        new_status = request.POST.get("status", "").strip()
        if new_status and new_status in dict(JobApplication.STATUS_CHOICES):
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            return redirect(reverse("company_application_detail", args=[application_id]))
    ctx = _company_base_context(request, "applications")
    ctx["application"] = application
    ctx["status_choices"] = JobApplication.STATUS_CHOICES
    return render(request, "company/application_detail.html", ctx)


def company_pending_approval_view(request):
    return render(request, "company_pending_approval.html")


def admin_approve_company_view(request, company_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            "<h1>403 Forbidden</h1><p>You must be logged in as an administrator to access this page.</p>"
            "<p><a href='/admin/login/'>Click here to log in</a></p>"
        )
    company = get_object_or_404(CompanyProfile, pk=company_id)
    company.is_approved = True
    company.save(update_fields=["is_approved"])
    subject = f"Votre compte entreprise '{company.company_name}' a été validé ! ✦"
    context = {
        "display_name": f"{company.user.first_name} {company.user.last_name}".strip() or company.user.username,
        "company_name": company.company_name,
        "ice": company.ice,
        "rc_number": company.rc_number,
        "city": company.city,
        "country": company.country,
    }
    send_html_email(
        subject=subject,
        template_name="emails/company_approved.html",
        context=context,
        recipient_list=[company.user.email],
    )
    return redirect("/admin/")


def admin_reject_company_view(request, company_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            "<h1>403 Forbidden</h1><p>You must be logged in as an administrator to access this page.</p>"
            "<p><a href='/admin/login/'>Click here to log in</a></p>"
        )
    company = get_object_or_404(CompanyProfile, pk=company_id)
    company.is_approved = False
    company.save(update_fields=["is_approved"])
    
    subject = f"Mise à jour concernant votre inscription entreprise '{company.company_name}'"
    context = {
        "display_name": f"{company.user.first_name} {company.user.last_name}".strip() or company.user.username,
        "company_name": company.company_name,
    }
    send_html_email(
        subject=subject,
        template_name="emails/company_rejected.html",
        context=context,
        recipient_list=[company.user.email],
    )
    return redirect("/admin/")


def admin_verify_company_offline_view(request, company_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden(
            "<h1>403 Forbidden</h1><p>You must be logged in as an administrator to access this page.</p>"
            "<p><a href='/admin/login/'>Click here to log in</a></p>"
        )
    company = get_object_or_404(CompanyProfile, pk=company_id)
    ctx = {
        "company": company,
        "verified_at": timezone.now(),
    }
    return render(request, "admin/verify_company_offline.html", ctx)

