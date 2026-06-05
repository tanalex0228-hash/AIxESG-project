from .models import AccountOperationLog
from .utils import get_user_organization


class AccountOperationLogMiddleware:
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.method in self.WRITE_METHODS:
            AccountOperationLog.objects.create(
                user=request.user,
                organization=get_user_organization(request.user),
                action=AccountOperationLog.ACTION_WRITE,
                path=request.path[:500],
                method=request.method,
                ip_address=self._ip_address(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"status_code": response.status_code},
            )
        return response

    def _ip_address(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
