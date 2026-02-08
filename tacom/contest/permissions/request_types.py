from contest.models import Contest
from contest.permissions.context import PermissionContext
from django.http import HttpRequest


class AppRequest(HttpRequest):
    perm: PermissionContext
    contest: Contest | None
