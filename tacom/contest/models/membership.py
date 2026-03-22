from contest.permissions.roles import CONTEST_ROLE_CAPABILITIES, Role
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL


class ContestMembership(models.Model):
    class ContestMembershipQuerySet(models.QuerySet):

        def with_roles(self):
            return self.prefetch_related("roles")

    objects = ContestMembershipQuerySet.as_manager()

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contest_memberships",
    )

    contest = models.ForeignKey(
        "contest.Contest",
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "contest")
        indexes = [
            models.Index(fields=["user", "contest"]),
        ]
        verbose_name = _("Staff")
        verbose_name_plural = _("Staff")

    def __str__(self):
        return f"{self.user} @ {self.contest}"

    @classmethod
    def set_role(cls, user, contest, role: Role, enabled: bool):
        role = role.value
        if enabled:
            # check if it's a role
            Role(role)

            membership, _ = cls.objects.get_or_create(
                user=user,
                contest=contest,
            )

            ContestMembershipRole.objects.get_or_create(
                membership=membership,
                role=role,
            )
        else:
            try:
                membership = cls.objects.get(user=user, contest=contest)
            except cls.DoesNotExist:
                return

            ContestMembershipRole.objects.filter(
                membership=membership,
                role=role,
            ).delete()

            if not membership.roles.exists():
                membership.delete()


class ContestMembershipRole(models.Model):
    membership = models.ForeignKey(
        ContestMembership,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    role = models.CharField(
        max_length=64,
        choices=[(role.value, role.name) for role in CONTEST_ROLE_CAPABILITIES.keys()],
    )

    class Meta:
        unique_together = ("membership", "role")
        verbose_name = _("Staff role")
        verbose_name_plural = _("Staff roles")

    def __str__(self):
        return f"{self.membership} → {self.role}"
