from types import MethodType

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.db.models import Count
from django.utils.html import format_html

try:
    import allauth.account.admin
    import allauth.socialaccount.admin
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
except Exception:
    EmailAddress = None
    SocialAccount = None
    SocialApp = None
    SocialToken = None


def _safe_unregister(model):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


for default_model in (User, Group, LogEntry):
    _safe_unregister(default_model)

for optional_model in (EmailAddress, SocialAccount, SocialApp, SocialToken):
    if optional_model is not None:
        _safe_unregister(optional_model)


@admin.register(User)
class ManageraHubUserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "full_name",
        "is_staff",
        "is_active",
        "email_state",
        "social_state",
        "date_joined",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined", "last_login")
    ordering = ("-date_joined",)
    search_fields = ("username", "email", "first_name", "last_name")
    list_select_related = ()
    list_per_page = 20

    @admin.display(description="Full name")
    def full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or "Unspecified"

    @admin.display(description="Email status")
    def email_state(self, obj):
        if EmailAddress is None:
            return "Unavailable"
        verified = EmailAddress.objects.filter(user=obj, verified=True).exists()
        label = "Verified" if verified else "Pending"
        css = "mh-badge success" if verified else "mh-badge warning"
        return format_html('<span class="{}">{}</span>', css, label)

    @admin.display(description="Social")
    def social_state(self, obj):
        if SocialAccount is None:
            return "Unavailable"
        count = SocialAccount.objects.filter(user=obj).count()
        label = f"{count} connected" if count else "Local only"
        css = "mh-badge accent" if count else "mh-badge muted"
        return format_html('<span class="{}">{}</span>', css, label)


@admin.register(Group)
class ManageraHubGroupAdmin(BaseGroupAdmin):
    list_display = ("name", "member_count", "permission_count")
    search_fields = ("name",)
    ordering = ("name",)

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.user_set.count()

    @admin.display(description="Permissions")
    def permission_count(self, obj):
        return obj.permissions.count()


@admin.register(LogEntry)
class ManageraHubLogEntryAdmin(admin.ModelAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag")
    list_filter = ("action_flag", "content_type", "action_time")
    search_fields = ("object_repr", "change_message", "user__username")
    ordering = ("-action_time",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


if EmailAddress is not None:
    @admin.register(EmailAddress)
    class EmailAddressAdmin(admin.ModelAdmin):
        list_display = ("email", "user", "verified", "primary")
        list_filter = ("verified", "primary")
        search_fields = ("email", "user__username", "user__email")
        ordering = ("-id",)
        autocomplete_fields = ("user",)


if SocialAccount is not None:
    @admin.register(SocialAccount)
    class SocialAccountAdmin(admin.ModelAdmin):
        list_display = ("user", "provider", "uid", "date_joined", "last_login")
        list_filter = ("provider", "date_joined", "last_login")
        search_fields = ("user__username", "user__email", "uid", "provider")
        ordering = ("-date_joined",)
        autocomplete_fields = ("user",)


if SocialToken is not None:
    @admin.register(SocialToken)
    class SocialTokenAdmin(admin.ModelAdmin):
        list_display = ("account", "app", "expires_at")
        list_filter = ("app__provider",)
        search_fields = ("account__user__username", "account__user__email", "app__name")
        ordering = ("-id",)
        autocomplete_fields = ("account", "app")


if SocialApp is not None:
    @admin.register(SocialApp)
    class SocialAppAdmin(admin.ModelAdmin):
        list_display = ("name", "provider", "client_id_preview", "site_total")
        list_filter = ("provider",)
        search_fields = ("name", "provider", "client_id")
        ordering = ("name",)
        filter_horizontal = ("sites",)

        @admin.display(description="Client ID")
        def client_id_preview(self, obj):
            prefix = obj.client_id[:18] if obj.client_id else ""
            return f"{prefix}..." if prefix else "Unavailable"

        @admin.display(description="Sites")
        def site_total(self, obj):
            return obj.sites.count()


admin.site.site_header = "ManageraHub Admin"
admin.site.site_title = "ManageraHub Admin"
admin.site.index_title = "Platform supervision"
admin.site.index_template = "admin/index.html"
admin.site.login_template = "admin/login.html"


def _managerahub_dashboard_context(self):
    user_queryset = User.objects.all()
    staff_total = user_queryset.filter(is_staff=True).count()
    active_total = user_queryset.filter(is_active=True).count()
    verified_total = EmailAddress.objects.filter(verified=True).count() if EmailAddress else 0
    social_total = SocialAccount.objects.count() if SocialAccount else 0
    provider_totals = {}
    recent_social_accounts = []
    if SocialAccount is not None:
        provider_totals = {
            row["provider"]: row["total"]
            for row in SocialAccount.objects.values("provider").annotate(total=Count("id")).order_by("provider")
        }
        recent_social_accounts = list(
            SocialAccount.objects.select_related("user").order_by("-date_joined")[:5]
        )
    recent_users = list(user_queryset.order_by("-date_joined")[:6])
    recent_admin_actions = list(
        LogEntry.objects.select_related("user", "content_type").order_by("-action_time")[:6]
    )
    app_cards = [
        {
            "label": "Users",
            "count": user_queryset.count(),
            "meta": f"{active_total} active",
            "link": "/admin/auth/user/",
        },
        {
            "label": "Verified emails",
            "count": verified_total,
            "meta": "Account trust signal",
            "link": "/admin/account/emailaddress/" if EmailAddress else "/admin/",
        },
        {
            "label": "Social accounts",
            "count": social_total,
            "meta": "Google and GitHub sign-ins",
            "link": "/admin/socialaccount/socialaccount/" if SocialAccount else "/admin/",
        },
        {
            "label": "Admin actions",
            "count": LogEntry.objects.count(),
            "meta": f"{staff_total} staff members",
            "link": "/admin/admin/logentry/",
        },
    ]
    feature_panels = [
        {
            "eyebrow": "User Management",
            "title": "Keep the member space organized and active",
            "description": "Review accounts, staff access, and core profile activity from one controlled space.",
            "bullets": [
                f"{active_total} active accounts ready to access the platform",
                f"{staff_total} staff members with administration access",
            ],
            "action": "Open users",
            "link": "/admin/auth/user/",
        },
        {
            "eyebrow": "Verification",
            "title": "Track email trust and account readiness",
            "description": "Monitor which users completed verification and which ones still need follow up.",
            "bullets": [
                f"{verified_total} verified email addresses",
                "Use the admin to validate account quality faster",
            ],
            "action": "View emails",
            "link": "/admin/account/emailaddress/" if EmailAddress else "/admin/",
        },
        {
            "eyebrow": "Platform Access",
            "title": "Watch social sign-ins and admin activity",
            "description": "See how people connect to ManageraHub and keep control over moderation actions.",
            "bullets": [
                f"{social_total} social accounts connected",
                f"{LogEntry.objects.count()} admin log entries recorded",
            ],
            "action": "View activity",
            "link": "/admin/admin/logentry/",
        },
    ]
    return {
        "dashboard_cards": app_cards,
        "feature_panels": feature_panels,
        "recent_users": recent_users,
        "recent_social_accounts": recent_social_accounts,
        "recent_admin_actions": recent_admin_actions,
        "provider_totals": provider_totals,
        "module_summary": [
            ("Accounts", user_queryset.count()),
            ("Staff", staff_total),
            ("Groups", Group.objects.count()),
            ("Sites", Site.objects.count()),
        ],
    }


def managerahub_index(self, request, extra_context=None):
    context = {}
    if extra_context:
        context.update(extra_context)
    context.update(_managerahub_dashboard_context(self))
    return AdminSite.index(self, request, extra_context=context)


admin.site.index = MethodType(managerahub_index, admin.site)
