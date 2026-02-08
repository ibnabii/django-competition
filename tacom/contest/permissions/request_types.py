from django.http import HttpRequest
from contest.models import Contest
from contest.permissions.context import PermissionContext


class AppRequest(HttpRequest):
    perm: PermissionContext
    contest: Contest | None
