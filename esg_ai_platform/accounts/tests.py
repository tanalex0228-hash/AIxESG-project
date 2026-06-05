from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings

from accounts.forms import RegistrationForm
from accounts.models import AccountOperationLog, Role, UserOrganizationRole, UserProfile
from accounts.utils import get_user_organization, is_individual_user, is_system_admin_user, user_has_admin_access
from organizations.models import Organization


class AccountOrganizationTests(TestCase):
    def test_user_organization_and_admin_role_resolution(self):
        user = get_user_model().objects.create_user(username="analyst", password="pass")
        organization = Organization.objects.create(name="Acme ESG")
        role = Role.objects.create(code=Role.ORG_ADMIN, name="Organization Admin")
        UserOrganizationRole.objects.create(user=user, organization=organization, role=role)

        self.assertEqual(get_user_organization(user), organization)
        self.assertFalse(user_has_admin_access(user))

    def test_enterprise_registration_creates_org_profile_role_and_log(self):
        form = RegistrationForm(
            data={
                "account_type": UserProfile.ACCOUNT_ENTERPRISE,
                "username": "enterprise-admin",
                "email": "enterprise@example.com",
                "secondary_email": "backup@example.com",
                "phone": "+886900000000",
                "legal_name": "Enterprise Admin",
                "password1": "StrongPass12345!",
                "password2": "StrongPass12345!",
                "organization_name": "Enterprise ESG Co",
                "tax_id": "12345678",
                "department": "Sustainability",
                "job_title": "ESG Manager",
                "accept_terms": True,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        profile = user.profile
        self.assertEqual(profile.account_type, UserProfile.ACCOUNT_ENTERPRISE)
        self.assertEqual(profile.secondary_email, "backup@example.com")
        with connection.cursor() as cursor:
            cursor.execute("select encrypted_secondary_email from accounts_userprofile where id = %s", [profile.id])
            stored_secondary_email = cursor.fetchone()[0]
        self.assertNotEqual(stored_secondary_email, "backup@example.com")
        self.assertTrue(stored_secondary_email.startswith("gAAAA"))
        self.assertTrue(user.organization_roles.filter(role__code=Role.ORG_ADMIN).exists())
        self.assertEqual(AccountOperationLog.objects.filter(action=AccountOperationLog.ACTION_REGISTER).count(), 1)

    def test_individual_registration_gets_public_viewer_profile(self):
        form = RegistrationForm(
            data={
                "account_type": UserProfile.ACCOUNT_INDIVIDUAL,
                "username": "reader",
                "email": "reader@example.com",
                "legal_name": "Reader User",
                "password1": "StrongPass12345!",
                "password2": "StrongPass12345!",
                "accept_terms": True,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(is_individual_user(user))
        self.assertTrue(hasattr(user, "individual_profile"))
        self.assertFalse(user.organization_roles.exists())

    @override_settings(SYSTEM_ADMIN_REGISTRATION_CODE="let-me-admin")
    def test_system_admin_registration_requires_code(self):
        form = RegistrationForm(
            data={
                "account_type": UserProfile.ACCOUNT_SYSTEM_ADMIN,
                "username": "sysadmin",
                "email": "sysadmin@example.com",
                "legal_name": "System Admin",
                "password1": "StrongPass12345!",
                "password2": "StrongPass12345!",
                "system_admin_registration_code": "let-me-admin",
                "accept_terms": True,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(user.is_staff)
        self.assertTrue(is_system_admin_user(user))
        self.assertTrue(user_has_admin_access(user))
