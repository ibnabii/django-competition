from django.contrib.auth import get_user_model
from django.db.models import Q


def delete_orphan_users():
    """
    Deletes all users that are:
    - not superusers
    - not staff
    - not referenced by any related model
    """
    User = get_user_model()

    protected_ids = set(
        User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).values_list(
            "id", flat=True
        )
    )

    referenced_ids = set()
    for related in User._meta.get_fields():
        if related.is_relation and related.one_to_many or related.one_to_one:
            accessor = related.get_accessor_name()
            try:
                ids = User.objects.filter(**{f"{accessor}__isnull": False}).values_list(
                    "id", flat=True
                )
                referenced_ids.update(ids)
            except Exception:
                pass  # skip non-standard accessors

    keep_ids = protected_ids | referenced_ids

    deleted_count, _ = User.objects.exclude(id__in=keep_ids).delete()
    return deleted_count
