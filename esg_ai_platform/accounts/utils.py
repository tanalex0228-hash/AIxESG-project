from .models import Role, UserProfile


def get_user_organization(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        rel = user.organization_roles.filter(is_active=True).select_related("organization").first()
        return rel.organization if rel else None
    profile = getattr(user, "profile", None)
    if profile and profile.default_organization:
        return profile.default_organization
    rel = user.organization_roles.filter(is_active=True).select_related("organization").first()
    return rel.organization if rel else None


def user_has_admin_access(user):
    return is_system_admin_user(user) or user.organization_roles.filter(role__code=Role.SUPER_ADMIN, is_active=True).exists()


def is_individual_user(user):
    profile = getattr(user, "profile", None)
    return bool(profile and profile.account_type == UserProfile.ACCOUNT_INDIVIDUAL)


def is_system_admin_user(user):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.account_type == UserProfile.ACCOUNT_SYSTEM_ADMIN)
