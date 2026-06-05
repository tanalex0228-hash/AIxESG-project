from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from organizations.models import Organization

from .models import (
    AccountOperationLog,
    EnterpriseUserProfile,
    IndividualUserProfile,
    Role,
    SystemAdminUserProfile,
    UserOrganizationRole,
    UserProfile,
)


class RegistrationForm(forms.Form):
    account_type = forms.ChoiceField(choices=UserProfile.ACCOUNT_TYPE_CHOICES, label="帳號類型")
    username = forms.CharField(max_length=150, label="登入帳號")
    email = forms.EmailField(label="主要電子信箱")
    secondary_email = forms.EmailField(required=False, label="備援電子信箱")
    phone = forms.CharField(max_length=40, required=False, label="備援電話")
    legal_name = forms.CharField(max_length=160, label="法定姓名 / 申請人姓名")
    password1 = forms.CharField(widget=forms.PasswordInput, label="密碼")
    password2 = forms.CharField(widget=forms.PasswordInput, label="確認密碼")
    organization_name = forms.CharField(max_length=255, required=False, label="企業名稱")
    tax_id = forms.CharField(max_length=64, required=False, label="統一編號 / 公司識別碼")
    department = forms.CharField(max_length=120, required=False, label="部門")
    job_title = forms.CharField(max_length=120, required=False, label="職稱")
    system_admin_registration_code = forms.CharField(
        max_length=120, required=False, widget=forms.PasswordInput, label="系統管理者註冊碼"
    )
    accept_terms = forms.BooleanField(label="我同意服務條款與資料留存政策")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("此登入帳號已被使用。")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError("此電子信箱已被使用。")
        return email

    def clean(self):
        cleaned = super().clean() or {}
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("兩次輸入的密碼不一致。")
        password = cleaned.get("password1")
        if password:
            validate_password(password)

        account_type = cleaned.get("account_type")
        if account_type == UserProfile.ACCOUNT_ENTERPRISE and not cleaned.get("organization_name"):
            raise forms.ValidationError("企業使用者必須填寫企業名稱。")
        if account_type == UserProfile.ACCOUNT_SYSTEM_ADMIN:
            expected_code = getattr(settings, "SYSTEM_ADMIN_REGISTRATION_CODE", "")
            if not expected_code or cleaned.get("system_admin_registration_code") != expected_code:
                raise forms.ValidationError("系統管理者註冊碼不正確。")
        return cleaned

    def save(self, request=None):
        account_type = self.cleaned_data["account_type"]
        user = get_user_model().objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
        )
        user.first_name = self.cleaned_data["legal_name"]
        if account_type == UserProfile.ACCOUNT_SYSTEM_ADMIN:
            user.is_staff = True
        user.save(update_fields=["email", "first_name", "is_staff"])

        organization = None
        if account_type == UserProfile.ACCOUNT_ENTERPRISE:
            organization, _ = Organization.objects.get_or_create(
                name=self.cleaned_data["organization_name"],
                defaults={"tax_id": self.cleaned_data.get("tax_id", "")},
            )

        profile = UserProfile.objects.create(
            user=user,
            default_organization=organization,
            account_type=account_type,
            legal_name=self.cleaned_data["legal_name"],
            job_title=self.cleaned_data.get("job_title", ""),
            encrypted_phone=self.cleaned_data.get("phone", ""),
            encrypted_secondary_email=self.cleaned_data.get("secondary_email", ""),
            terms_accepted_at=timezone.now(),
            data_retention_consent_at=timezone.now(),
        )

        if account_type == UserProfile.ACCOUNT_INDIVIDUAL:
            IndividualUserProfile.objects.create(user=user, display_name=self.cleaned_data["legal_name"])
            role = self._role(Role.VIEWER, "Viewer")
        elif account_type == UserProfile.ACCOUNT_ENTERPRISE:
            EnterpriseUserProfile.objects.create(
                user=user,
                organization=organization,
                department=self.cleaned_data.get("department", ""),
                business_title=self.cleaned_data.get("job_title", ""),
            )
            role = self._role(Role.ORG_ADMIN, "Organization Admin")
            UserOrganizationRole.objects.create(user=user, organization=organization, role=role)
        else:
            SystemAdminUserProfile.objects.create(user=user, approval_reference="self-registration-code")
            role = self._role(Role.SUPER_ADMIN, "Super Admin")

        AccountOperationLog.objects.create(
            user=user,
            organization=organization,
            action=AccountOperationLog.ACTION_REGISTER,
            path=getattr(request, "path", "") if request else "",
            method=getattr(request, "method", "") if request else "",
            ip_address=self._ip_address(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "") if request else "",
            metadata={"account_type": account_type, "profile_id": profile.id, "role": role.code},
        )
        return user

    def _role(self, code, name):
        return Role.objects.get_or_create(code=code, defaults={"name": name})[0]

    def _ip_address(self, request):
        if not request:
            return None
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
