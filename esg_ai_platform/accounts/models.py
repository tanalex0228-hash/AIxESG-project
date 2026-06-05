from django.conf import settings
from django.db import models

from organizations.models import Organization

from .fields import EncryptedTextField


class Role(models.Model):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "organization_admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    ROLE_CHOICES = [
        (SUPER_ADMIN, "Super Admin"),
        (ORG_ADMIN, "Organization Admin"),
        (ANALYST, "Analyst"),
        (VIEWER, "Viewer"),
    ]

    code = models.CharField(max_length=40, choices=ROLE_CHOICES, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ACCOUNT_INDIVIDUAL = "individual"
    ACCOUNT_ENTERPRISE = "enterprise"
    ACCOUNT_SYSTEM_ADMIN = "system_admin"
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_INDIVIDUAL, "Individual User"),
        (ACCOUNT_ENTERPRISE, "Enterprise User"),
        (ACCOUNT_SYSTEM_ADMIN, "System Administrator"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    default_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="default_users"
    )
    account_type = models.CharField(max_length=40, choices=ACCOUNT_TYPE_CHOICES, default=ACCOUNT_ENTERPRISE)
    legal_name = models.CharField(max_length=160, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    encrypted_phone = EncryptedTextField(blank=True)
    encrypted_secondary_email = EncryptedTextField(blank=True)
    primary_email_verified = models.BooleanField(default=False)
    backup_contact_verified = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    data_retention_consent_at = models.DateTimeField(null=True, blank=True)
    monthly_analysis_count = models.PositiveIntegerField(default=0)
    usage_quota = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()

    @property
    def phone(self):
        return self.encrypted_phone

    @property
    def secondary_email(self):
        return self.encrypted_secondary_email


class IndividualUserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="individual_profile")
    display_name = models.CharField(max_length=160)
    research_interest = models.CharField(max_length=255, blank=True)
    can_view_public_company_reports = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class EnterpriseUserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enterprise_profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="enterprise_profiles")
    department = models.CharField(max_length=120, blank=True)
    business_title = models.CharField(max_length=120, blank=True)
    can_upload_reports = models.BooleanField(default=True)
    can_view_own_organization_only = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.organization}"


class SystemAdminUserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="system_admin_profile")
    admin_scope = models.CharField(max_length=120, default="platform")
    can_modify_system_rules = models.BooleanField(default=True)
    can_publish_announcements = models.BooleanField(default=True)
    approval_reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"System admin: {self.user}"


class UserOrganizationRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_roles")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "organization", "role")

    def __str__(self):
        return f"{self.user} - {self.organization} - {self.role}"


class LoginLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_logs")
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class AccountOperationLog(models.Model):
    ACTION_REGISTER = "register"
    ACTION_LOGIN = "login"
    ACTION_WRITE = "write"
    ACTION_RULE_CHANGE = "rule_change"
    ACTION_UPLOAD = "upload"
    ACTION_CHOICES = [
        (ACTION_REGISTER, "Register"),
        (ACTION_LOGIN, "Login"),
        (ACTION_WRITE, "Write"),
        (ACTION_RULE_CHANGE, "Rule Change"),
        (ACTION_UPLOAD, "Upload"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=12, blank=True)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
