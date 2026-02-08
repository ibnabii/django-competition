from contest.permissions.context import PermissionContext


class PermissionMiddleware:
    """
    Attaches PermissionContext to request.perm
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.perm = PermissionContext(request.user)
        return self.get_response(request)
