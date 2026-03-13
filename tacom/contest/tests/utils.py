from random import choice

from django.contrib.auth import get_user_model
from django.db.models import Q

from contest.factories.category_factory import CategoryFactory
from contest.factories.contest_factory import ContestState, PeriodState, ContestFactory
from contest.factories.entry_factory import EntryFactory
from contest.factories.style_factory import StyleFactory
from contest.factories.user_factory import UserFactory, JudgeApplicationFactory


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


def create_test_competition(
    title,
    categories_cnt=5,
    entries_cnt=50,
    judges_cnt=40,
    participants_cnt=20,
    contest_state=None,
):
    if not contest_state:
        contest_state = ContestState(
            delivery=PeriodState.before,
            judging=PeriodState.before,
            result_is_published=False,
            is_judging_bos=False,
            is_judging_finals=False,
            is_judging_eliminations=False,
        )

    style_names = [
        "Miody tradycyjne",
        "Miody korzenne i przyprawowe",
        "Miody owocowe",
        "Miody eksperymentalne",
        "Miody sesyjne",
    ]
    if len(style_names) < categories_cnt:
        for i in range(categories_cnt - len(style_names)):
            style_names.append(f"Inny styl {i+1}")
    elif len(style_names) > categories_cnt:
        style_names = style_names[:categories_cnt]

    styles = [
        StyleFactory(
            name=s,
            description=f"{s} description in EN",
            description_pl=f"{s} description in EN",
        )
        for s in style_names
    ]

    categories = [CategoryFactory(style=style) for style in styles]

    contest = ContestFactory(title=title, _state=contest_state, categories=categories)

    brewers = [UserFactory(profile=True) for _ in range(participants_cnt)]

    entries = [
        EntryFactory(
            category=choice(contest.categories.all()),
            brewer=choice(brewers),
            is_received=True,
            is_paid=True,
        )
        for _ in range(entries_cnt)
    ]

    # add some undelivered

    for i in range(1, 6):
        EntryFactory(
            category=choice(contest.categories.all()),
            brewer=choice(brewers),
            is_received=not bool(i % 2),
            is_paid=not bool(i % 3),
        )

    judge_applications = [
        JudgeApplicationFactory(contest=contest) for _ in range(judges_cnt)
    ]

    # turn some judges into mjp
    for i, judge_application in enumerate(judge_applications):
        if i % 2 == 0:
            judge_application.user.judge_certification.is_mjp = True
            judge_application.user.judge_certification.mjp_level = [1, 2, 3, 4, 5][
                i % 5
            ]
            judge_application.user.judge_certification.save()
