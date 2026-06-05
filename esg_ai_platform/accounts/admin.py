from django.contrib import admin

from .models import (
    AccountOperationLog,
    EnterpriseUserProfile,
    IndividualUserProfile,
    LoginLog,
    Role,
    SystemAdminUserProfile,
    UserOrganizationRole,
    UserProfile,
)

admin.site.register(Role)
admin.site.register(UserProfile)
admin.site.register(IndividualUserProfile)
admin.site.register(EnterpriseUserProfile)
admin.site.register(SystemAdminUserProfile)
admin.site.register(UserOrganizationRole)
admin.site.register(LoginLog)
admin.site.register(AccountOperationLog)
